import time
from hexapod import Robot

robot = Robot('192.168.137.196')
positions = {1: -240, 2: -150, 3: 145}
phases = [(2, 240), (3, 0), (1, 150), (3, -175),
          (1, -240), (3, 0), (2, -150)]
try:
    for joint, target in phases:
        start = positions[joint]
        steps = max(1, (abs(target - start) + 9) // 10)
        for n in range(1, steps + 1):
            value = round(start + (target - start) * n / steps)
            robot.command(f'JOG {joint} {value}')
            time.sleep(.2)
        positions[joint] = target
finally:
    robot.command('STOP')
    robot.close()
