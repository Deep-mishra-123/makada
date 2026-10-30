import time
import sys
from hexapod import Robot

robot = Robot('192.168.137.196')
positions = {1: 0, 2: 0, 3: 0}
phases = [(3, 145), (2, 240), (3, 0), (1, 150),
          (3, -175), (1, -240), (3, 0), (2, -150)]
try:
    for joint in (1, 2, 3):
        robot.command(f'ENABLE {joint}')
        time.sleep(1)
    for cycle in range(int(sys.argv[1]) if len(sys.argv) > 1 else 5):
        for joint, target in phases:
            start = positions[joint]
            steps = max(1, (abs(target - start) + 9) // 10)
            for n in range(1, steps + 1):
                value = round(start + (target - start) * n / steps)
                robot.command(f'JOG {joint} {value}')
                time.sleep(.18)
            positions[joint] = target
        print(f'CYCLE {cycle + 1} COMPLETE', flush=True)
finally:
    robot.command('STOP')
    robot.close()
