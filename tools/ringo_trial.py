import math
import time
from hexapod import Robot

robot = Robot('192.168.137.196')
try:
    for joint in (1, 2, 3):
        robot.command(f'ENABLE {joint}')
        time.sleep(0.8)
    start = time.monotonic()
    while True:
        t = min((time.monotonic() - start) / 8, 1.0)
        envelope = math.sin(math.pi * t)
        wave = math.sin(2 * math.pi * t) * envelope
        tilt = math.cos(2 * math.pi * t) * envelope
        for joint, offset in enumerate((-15 * wave, 15 * wave, 14 * tilt), 1):
            robot.command(f'JOG {joint} {round(offset)}')
        if t >= 1:
            break
        time.sleep(0.12)
finally:
    robot.command('STOP')
    robot.close()
