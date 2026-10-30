"""USB/Wi-Fi bench controller. Check mode requires the motor battery unplugged."""
import argparse
import json
from pathlib import Path
import re
import time

import serial


class Board:
    def __init__(self, port, host=None, token=None):
        if host:
            self.link = serial.serial_for_url(f"socket://{host}:8266", timeout=0.15,
                                              write_timeout=1)
            try:
                self.send(f"AUTH {token}", "OK AUTH")
            except BaseException:
                self.link.close()
                raise
            return
        self.link = serial.Serial(port=None, baudrate=115200, timeout=0.15,
                                  write_timeout=1)
        self.link.dtr = False
        self.link.rts = False
        self.link.port = port
        self.link.open()
        time.sleep(3.2)
        self.link.reset_input_buffer()

    def send(self, command, expected):
        self.link.write((command + "\n").encode("ascii"))
        return self.wait(expected)

    def wait(self, expected, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            reply = self.link.readline().decode("ascii", errors="replace").strip()
            if reply:
                print(reply)
                if reply.startswith(expected):
                    return reply
                if reply.startswith("STOP"):
                    raise RuntimeError(f"Unexpected stop while waiting for {expected}: {reply}")
        raise TimeoutError(f"No response matching {expected}")

    def hold(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.send("PING", "OK PING")
            time.sleep(min(0.15, max(0, deadline - time.monotonic())))

    def close(self):
        try:
            self.send("STOP", "STOP requested")
        finally:
            self.link.close()


def check(board):
    reply = board.send("STATUS", "STATUS")
    assert "armed=0 pulse_us=1000" in reply
    assert "motor_led_active=0" in reply
    board.send("STOP", "STOP requested")
    board.send("SET 1020", "STOP set_rejected")
    board.send("ARM", "OK ARM")
    board.send("SET 1020", "OK SET 1020")
    reply = board.send("STATUS", "STATUS")
    assert "armed=1 pulse_us=1020" in reply
    assert "motor_led_active=1" in reply
    board.hold(0.4)
    board.send("STOP", "STOP requested")
    assert "motor_led_active=0" in board.send("STATUS", "STATUS")
    board.send("ARM", "OK ARM")
    board.send("SET 1101", "STOP set_rejected")
    board.send("ARM", "OK ARM")
    board.send("SET 1020junk", "STOP set_rejected")
    board.send("ARM", "OK ARM")
    board.send("SET 1020", "OK SET 1020")
    board.wait("STOP link_timeout")
    assert "armed=0 pulse_us=1000" in board.send("STATUS", "STATUS")
    board.send("ARM", "OK ARM")
    board.send("SET 1020", "OK SET 1020")
    # Continue heartbeats until the independent three-second limit fires.
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        reply = board.send("PING", ("OK PING", "STOP bench_time_limit"))
        if reply == "STOP bench_time_limit":
            break
        time.sleep(0.15)
    else:
        raise AssertionError("Armed run limit did not fire")
    assert "armed=0 pulse_us=1000" in board.send("STATUS", "STATUS")
    board.send("ARM", "OK ARM")
    board.send("X" * 120, "STOP invalid_line")
    assert "armed=0 pulse_us=1000" in board.send("STATUS", "STATUS")
    print("PASS: disarmed boot/state, command control, limits, malformed input, heartbeat and run timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "stop", "check", "pulse", "discover", "limit", "idle", "beep"])
    parser.add_argument("--port", default="COM18")
    parser.add_argument("--host", help="NodeMCU IP address, or 'auto' for the locally saved IP")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().parents[1] / ".local/wifi.json")
    parser.add_argument("--battery-disconnected", action="store_true")
    parser.add_argument("--pulse-us", type=int, default=1020)
    parser.add_argument("--limit-us", type=int, default=1100)
    parser.add_argument("--idle-us", type=int, default=1000)
    parser.add_argument("--frequency", type=int, default=440)
    parser.add_argument("--duration-ms", type=int, default=250)
    parser.add_argument("--seconds", type=float, default=1)
    args = parser.parse_args()
    if args.action == "check" and not args.battery_disconnected:
        parser.error("check requires --battery-disconnected; it emits test throttle signals")
    if not 200 <= args.frequency <= 2000 or not 1 <= args.duration_ms <= 500:
        parser.error("frequency must be 200..2000 Hz and duration 1..500 ms")
    if not 900 <= args.idle_us <= 1000 or not 1000 <= args.pulse_us <= 2000 or not 1000 <= args.limit_us <= 2000 or not 0 < args.seconds <= 2:
        parser.error("pulse and limit must be 1000..2000 us and duration must be >0 and <=2 seconds")
    token = None
    if args.host:
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        token = config["token"]
        if args.host == "auto":
            args.host = config.get("host")
            if not args.host:
                parser.error("No saved board IP; read it with USB status and use --host IP")
    board = Board(args.port, args.host, token)
    try:
        if args.action == "check":
            check(board)
        elif args.action == "pulse":
            board.send("STOP", "STOP requested")
            board.send("ARM", "OK ARM")
            board.send(f"SET {args.pulse_us}", f"OK SET {args.pulse_us}")
            board.hold(args.seconds)
        elif args.action == "status":
            board.send("STATUS", "STATUS")
        elif args.action == "limit":
            board.send(f"LIMIT {args.limit_us}", f"OK LIMIT {args.limit_us}")
        elif args.action == "idle":
            board.send(f"IDLE {args.idle_us}", f"OK IDLE {args.idle_us}")
        elif args.action == "beep":
            board.send(f"BEEP {args.frequency} {args.duration_ms}",
                       f"OK BEEP {args.frequency} {args.duration_ms}")
        elif args.action == "discover":
            reply = board.send("STATUS", "STATUS")
            match = re.search(r"wifi=1 ip=([0-9.]+)", reply)
            if not match:
                raise RuntimeError("Board has not joined the hotspot yet; retry in a few seconds")
            config = json.loads(args.config.read_text(encoding="utf-8-sig"))
            config["host"] = match.group(1)
            args.config.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print(f"Saved board IP: {config['host']}")
        else:
            board.send("STOP", "STOP requested")
    finally:
        board.close()


if __name__ == "__main__":
    main()
