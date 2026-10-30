import time
from hexapod import Robot

robot = Robot('192.168.137.196')
try:
    robot.command('STOP')
    robot.command('LIMIT 1 1210 1600')
    robot.command('CAL 1 1450 -1 150')
    for joint in (1, 2, 3):
        robot.command(f'ENABLE {joint}')
        time.sleep(.5)
        robot.command('PING')
    position = 0
    for target in (140, 0, -160, 0):
        count = abs(target - position) // 5
        start = position
        for n in range(1, count + 1):
            value = round(start + (target - start) * n / count)
            robot.command(f'JOG 3 {value}')
            time.sleep(.03)
        position = target
        robot.command('PING')
        time.sleep(.4)
finally:
    robot.command('STOP')
    robot.close()
