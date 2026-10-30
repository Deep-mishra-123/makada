"""One centered-start trial of the tested gait with shorter update pauses."""
import time
import sys
from hexapod import Robot

robot = Robot('192.168.137.196')
positions = {1: 0, 2: 0, 3: 0}
phases = [(3, 140), (2, 240), (3, 0), (1, 150),
          (3, -160), (1, -240), (3, 0), (2, -150)]
try:
    robot.command('STOP')
    for joint in (1, 2, 3):
        robot.command(f'ENABLE {joint}')
        time.sleep(1)
    for cycle in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1):
        for joint, target in phases:
            start = positions[joint]
            count = max(1, (abs(target - start) + 4) // 5)
            for n in range(1, count + 1):
                offset = round(start + (target - start) * n / count)
                robot.command(f'JOG {joint} {offset}')
                time.sleep(.075)
            positions[joint] = target
            time.sleep(.5)
            print(f'PHASE joint={joint} offset={target} COMPLETE', flush=True)
        print(f'CYCLE {cycle + 1} COMPLETE', flush=True)
finally:
    try:
        robot.command('STOP')
    except Exception:
        robot.close()
        robot = Robot('192.168.137.196')
        robot.command('STOP')
    finally:
        robot.close()
