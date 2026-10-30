import time
from hexapod import Robot

robot = Robot('192.168.137.196')
# Continues the current powered test pose; does not enable or recenter servos.
positions = {1: 100, 2: 100, 3: 0}
phases = [(3, -160), (1, -100), (3, 0), (2, -100),
          (3, 100), (2, 100), (3, 0), (1, 100)]
try:
    status = robot.command('STATUS')
    if 'enabled_mask=7 ' not in status or 'running=0 ' not in status:
        raise RuntimeError('Expected all servos enabled with no autonomous motion')
    for joint, target in phases:
        start = positions[joint]
        steps = max(1, abs(target - start) // 5)
        for n in range(1, steps + 1):
            value = round(start + (target - start) * n / steps)
            robot.command(f'JOG {joint} {value}')
            time.sleep(.25)
        positions[joint] = target
        print(f'PHASE joint={joint} offset={target} COMPLETE', flush=True)
finally:
    robot.command('STOP')
    robot.close()
