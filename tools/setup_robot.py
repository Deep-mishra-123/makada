"""Portable credentials, address discovery, and calibration backup. No automatic motion."""
import argparse
import getpass
import ipaddress
import json
import re
import secrets
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / '.local' / 'wifi.json'


def read_config():
    if not CONFIG.exists():
        raise RuntimeError('Run init first or privately copy .local/wifi.json from the original PC.')
    return json.loads(CONFIG.read_text(encoding='utf-8-sig'))


def write_config(config):
    CONFIG.parent.mkdir(exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


def header(config):
    fields = {'BENCH_SSID': config['ssid'], 'BENCH_PASSWORD': config['password'],
              'BENCH_TOKEN': config['token']}
    text = '#pragma once\n' + ''.join(f'#define {key} {json.dumps(value)}\n' for key, value in fields.items())
    (ROOT / 'include').mkdir(exist_ok=True)
    (ROOT / 'include' / 'secrets.h').write_text(text, encoding='utf-8')


def initialize(args):
    if CONFIG.exists():
        config = read_config()  # Never silently rotate an already-flashed board's credentials.
    else:
        password = getpass.getpass('Existing hotspot password (Enter to generate): ') if args.existing else secrets.token_hex(10)
        if not password:
            password = secrets.token_hex(10)
        if not 8 <= len(password) <= 63 or not password.isascii():
            raise ValueError('Hotspot password must be 8–63 ASCII characters.')
        config = {'ssid': args.ssid, 'password': password, 'token': secrets.token_hex(24), 'host': ''}
        write_config(config)
    header(config)
    print('Local credentials and include/secrets.h are ready. Both are excluded from git.')
    print('Use tools/hotspot.ps1 on Windows, then flash hexapod firmware if these credentials are new.')


def verify_host(host, config):
    # Authenticate before trusting an address; never send ENABLE, JOG, or RUN.
    ipaddress.IPv4Address(host)
    with socket.create_connection((host, 8266), timeout=2) as connection:
        with connection.makefile('rb') as reader:
            connection.sendall(('AUTH ' + config['token'] + '\n').encode('ascii'))
            if reader.readline().strip() != b'OK AUTH':
                raise RuntimeError('Authentication failed. Use the credentials flashed on this board.')
            connection.sendall(b'STATUS\n')
            status = reader.readline().decode('ascii').strip()
            if not status.startswith('STATUS ') or 'enabled_mask=' not in status:
                raise RuntimeError('Address is not running the expected hexapod firmware.')
    config['host'] = host
    write_config(config)
    print(f'Verified and saved NodeMCU address: {host}')
    print(status)


def discover(args):
    config = read_config()
    if args.host:
        verify_host(args.host, config)
        return
    if args.port:
        if not args.servo_power_disconnected:
            raise ValueError('USB discovery can reset the MCU; use --servo-power-disconnected after unplugging the LiPo.')
        import serial
        candidates = []
        with serial.Serial(args.port, 115200, timeout=.2) as board:
            # Explicit reset is safe only with servo power disconnected.
            board.dtr = False
            board.rts = True
            time.sleep(.1)
            board.rts = False
            end = time.monotonic() + 20
            while time.monotonic() < end:
                line = board.readline().decode('ascii', errors='ignore')
                match = re.search(r'ip=(\d+\.\d+\.\d+\.\d+)', line)
                if match and match.group(1) != '0.0.0.0':
                    candidates.append(match.group(1))
                    break
    else:
        # Cached neighbors only; no arbitrary subnet scanning.
        candidates = [config.get('host', '')]
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, check=False)
        candidates += re.findall(r'(?m)^\s*(\d+\.\d+\.\d+\.\d+)\s+[0-9a-f:-]{17}\s+', result.stdout, re.I)
    for host in dict.fromkeys(candidates):
        if not host:
            continue
        try:
            verify_host(host, config)
            return
        except (OSError, RuntimeError, ValueError):
            continue
    raise RuntimeError('Board not found. Check 2.4 GHz hotspot and credentials. Use discover --host IP from hotspot device list, or discover --port COMx --servo-power-disconnected.')


def snapshot(args):
    from hexapod import Robot
    robot = Robot(args.host)
    try:
        robot.socket.sendall(b'CONFIG\n')
        joints = []
        while True:
            line = robot.reader.readline().decode('ascii').strip()
            if line == 'OK CONFIG':
                break
            if not line.startswith('CONFIG '):
                raise RuntimeError('Invalid calibration response')
            joints.append({key: int(value) for key, value in re.findall(r'(\w+)=(-?\d+)', line)})
        timing = robot.command('TIMING')
        values = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', timing)}
        if len(joints) != 3:
            raise RuntimeError('Incomplete calibration response')
        profile = {'description': 'Live board snapshot; physical clearance depends on this assembly.',
                   'joints': joints, 'timing': values}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
        print(f'Saved calibration without Wi-Fi credentials: {args.output}')
    finally:
        robot.close()


def restore(args):
    if not args.servo_power_disconnected:
        raise ValueError('Restore is for unpowered servos; unplug LiPo and use --servo-power-disconnected.')
    from hexapod import Robot
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    joints = profile['joints']
    if sorted(item['joint'] for item in joints) != [1, 2, 3]:
        raise ValueError('Profile must contain joints 1, 2 and 3 exactly once')
    for item in joints:
        if not (900 <= item['min'] < item['center'] < item['max'] <= 2100 and
                item['sign'] in (-1, 1) and 10 <= item['amplitude'] <= 600 and
                item['center'] - item['amplitude'] >= item['min'] and
                item['center'] + item['amplitude'] <= item['max']):
            raise ValueError('Invalid calibration profile')
    timing = profile['timing']
    if not (20 <= timing['move_ms'] <= 60000 and 0 <= timing['settle_ms'] <= 60000):
        raise ValueError('Invalid timing profile')
    robot = Robot(args.host)
    try:
        robot.command('STOP')
        for item in joints:
            joint = item['joint']
            # A temporary broad envelope permits changing center/amplitude in either direction.
            # Outputs remain detached throughout; the final limits are then applied.
            robot.command(f'LIMIT {joint} 900 2100')
            robot.command(f"CAL {joint} {item['center']} {item['sign']} {item['amplitude']}")
            robot.command(f"LIMIT {joint} {item['min']} {item['max']}")
        robot.command(f"TIMING {timing['move_ms']} {timing['settle_ms']}")
        robot.command('STATUS')
        print('Profile restored. Verify mechanical clearance before applying servo power.')
    finally:
        robot.command('STOP')
        robot.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init')
    init.add_argument('--ssid', default='CutieCircuits-Bench')
    init.add_argument('--existing', action='store_true', help='Prompt privately for an existing hotspot password')
    sub.add_parser('header')
    find = sub.add_parser('discover')
    find.add_argument('--host')
    find.add_argument('--port')
    find.add_argument('--servo-power-disconnected', action='store_true')
    snap = sub.add_parser('snapshot')
    snap.add_argument('--host')
    snap.add_argument('--output', type=Path, default=ROOT / '.local' / 'calibration.json')
    apply = sub.add_parser('restore')
    apply.add_argument('profile', type=Path)
    apply.add_argument('--host')
    apply.add_argument('--servo-power-disconnected', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'init':
            initialize(args)
        elif args.action == 'header':
            header(read_config())
            print('Generated local firmware header.')
        elif args.action == 'discover':
            discover(args)
        elif args.action == 'snapshot':
            snapshot(args)
        else:
            restore(args)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
