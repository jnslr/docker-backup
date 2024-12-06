import time
import schedule

from backup import runBackup


schedule.every(1).minutes.do(runBackup)
#schedule.every(1).seconds.do(lambda:print('hello'))


while True:
    schedule.run_pending()
    time.sleep(1)