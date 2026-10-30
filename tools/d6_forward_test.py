import time
from hexapod import Robot

robot = Robot('192.168.137.196')
try:
    robot.command('STOP')
    robot.command('LIMIT 2 1350 1850')
    robot.command('ENABLE 3')
    time.sleep(.5)
    for value in range(5, 141, 5):
        robot.command(f'JOG 3 {value}')
        time.sleep(.08)
    robot.command('ENABLE 2')
    time.sleep(.5)
    for value in range(5, 351, 5):
        robot.command(f'JOG 2 {value}')
        time.sleep(.1)
    print('D6 AT +350; HOLDING FOR 30 SECONDS', flush=True)
    for _ in range(60):
        robot.command('PING')
        time.sleep(.5)
finally:
    robot.command('STOP')
    robot.close()
