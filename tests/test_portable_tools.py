import argparse
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hexapod
import setup_robot


class FakeSocket:
    def __init__(self, replies):
        self.reader = io.BytesIO(replies)
        self.sent = []

    def setsockopt(self, *args):
        pass

    def makefile(self, *args):
        return self.reader

    def sendall(self, message):
        self.sent.append(message)

    def close(self):
        pass


class PortableToolsTests(unittest.TestCase):
    def test_initialization_reuses_private_credentials_and_escapes_header(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / '.local/wifi.json'
            with patch.object(setup_robot, 'ROOT', root), patch.object(setup_robot, 'CONFIG', config_path):
                args = argparse.Namespace(existing=False, ssid='Test Hotspot')
                setup_robot.initialize(args)
                first = setup_robot.read_config()
                setup_robot.initialize(args)
                self.assertEqual(first, setup_robot.read_config())
                first['password'] = 'a"b\\cdefgh'
                setup_robot.header(first)
                self.assertIn(json.dumps(first['password']), (root / 'include/secrets.h').read_text())

    def test_saved_address_and_unsolicited_completion_do_not_shift_replies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wifi.json'
            path.write_text(json.dumps({'host': '192.0.2.10', 'token': 'test-token'}))
            link = FakeSocket(b'OK AUTH\nDONE\nSTATUS running=0\nOK STOP\n')
            with patch.object(hexapod, 'CONFIG', path), patch.object(hexapod.socket, 'create_connection', return_value=link) as connect:
                robot = hexapod.Robot()
                self.assertEqual(robot.command('STATUS'), 'STATUS running=0')
                self.assertEqual(robot.command('STOP'), 'OK STOP')
                connect.assert_called_once_with(('192.0.2.10', 8266), timeout=3)
                robot.close()

    def test_snapshot_contains_calibration_but_no_token(self):
        replies = (b'CONFIG joint=1 center=1450 min=1260 max=1600 sign=-1 amplitude=150\n'
                   b'CONFIG joint=2 center=1500 min=1350 max=1740 sign=1 amplitude=150\n'
                   b'CONFIG joint=3 center=1505 min=1330 max=1650 sign=1 amplitude=140\nOK CONFIG\n')
        class SnapshotRobot:
            def __init__(self, host):
                self.socket = FakeSocket(replies)
                self.reader = self.socket.reader
            def command(self, value):
                return 'TIMING move_ms=25 settle_ms=25'
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as directory, patch.object(hexapod, 'Robot', SnapshotRobot):
            output = Path(directory) / 'profile.json'
            setup_robot.snapshot(argparse.Namespace(host=None, output=output))
            profile = json.loads(output.read_text())
            self.assertEqual(len(profile['joints']), 3)
            self.assertEqual(profile['timing']['move_ms'], 25)
            self.assertNotIn('token', profile)

    def test_restore_requires_unpowered_servos_and_never_enables(self):
        source = Path(__file__).resolve().parents[1] / 'profiles/spidey-last-known.json'
        args = argparse.Namespace(profile=source, host=None, servo_power_disconnected=False)
        with self.assertRaises(ValueError):
            setup_robot.restore(args)
        commands = []
        class RestoreRobot:
            def __init__(self, host):
                pass
            def command(self, command):
                commands.append(command)
            def close(self):
                pass
        args.servo_power_disconnected = True
        with patch.object(hexapod, 'Robot', RestoreRobot):
            setup_robot.restore(args)
        self.assertFalse(any(command.startswith(('ENABLE', 'JOG', 'RUN')) for command in commands))
        self.assertIn('LIMIT 1 1260 1600', commands)
        self.assertEqual(commands[-1], 'STOP')


if __name__ == '__main__':
    unittest.main()
