import os
import time
import schedule

from backup import runBackup


schedule.every().day.at("02:00").do(runBackup)

if os.getenv("INITIAL_RUN","FALSE").lower() == "true":
    runBackup()

while True:
    schedule.run_pending()
    time.sleep(1)