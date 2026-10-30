import time
import sys
from hexapod import Robot

robot = Robot('192.168.137.196')
positions = {1: 0, 2: 0, 3: 0}
try:
    robot.command('STOP')
    for joint in (1, 2, 3):
        robot.command(f'ENABLE {joint}')
        time.sleep(.5)
        robot.command('PING')
    phases = ((3, -160), (1, -240), (3, 0), (2, -150)) if '--second' in sys.argv else ((3, 140), (2, 240), (3, 0), (1, 150))
    for joint, target in phases:
        start = positions[joint]
        for n in range(1, 21):
            robot.command(f'JOG {joint} {round(start + (target - start) * n / 20)}')
            time.sleep(.05)
        positions[joint] = target
        robot.command('PING')
        time.sleep(.5)
finally:
    robot.command('STOP')
    robot.close()
