"""Continue the confirmed powered pose through five slow bench gait cycles."""
import time
from hexapod import Robot

HOST = '192.168.137.196'
robot = Robot(HOST)
positions = {1: -240, 2: -150, 3: 0}
phases = [(3, 140), (2, 240), (3, 0), (1, 150),
          (3, -160), (1, -240), (3, 0), (2, -150)]
try:
    status = robot.command('STATUS')
    if 'enabled_mask=7 ' not in status or 'running=0 ' not in status:
        raise RuntimeError('Expected all three signals enabled, no autonomous run')
    diag = robot.command('DIAG')
    if 'commanded=1210,1350,1505' not in diag:
        raise RuntimeError('Starting command positions differ from confirmed pose')
    for cycle in range(5):
        for joint, target in phases:
            start = positions[joint]
            count = max(1, (abs(target - start) + 4) // 5)
            for n in range(1, count + 1):
                offset = round(start + (target - start) * n / count)
                robot.command(f'JOG {joint} {offset}')
                time.sleep(.3)
            positions[joint] = target
            print(f'PHASE joint={joint} offset={target} COMPLETE', flush=True)
        print(f'CYCLE {cycle + 1}/5 COMPLETE', flush=True)
finally:
    try:
        robot.command('STOP')
    except Exception:
        robot.close()
        robot = Robot(HOST)
        robot.command('STOP')
    finally:
        robot.close()
