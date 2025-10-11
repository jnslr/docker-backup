import logging
import datetime
import time
import schedule

from config.config import ConfigHelper
from dockerHelper.helper import DockerHelper
from remotes.helper import RemoteHelper
from backup.helper import BackupHelper
from backup.worker import BackupWorker
from server.server import Server

# # #TODO Debug code
# from dotenv import load_dotenv
# load_dotenv()

logging.basicConfig(handlers=[logging.StreamHandler()], format=logging.BASIC_FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)


logger.info(f"######################################################################")
logger.info(f"Docker Backup service started")
logger.info(f"######################################################################")

configHelper = ConfigHelper()
dockerHelper = DockerHelper()
remoteHelper = RemoteHelper()
backupHelper = BackupHelper()
backupWorker = BackupWorker()
server       = Server()

server.startServer()


remoteList = remoteHelper.getRemotes()

for remote in remoteList:
    backupInfo   = []
    connectionOk = remote.testConnection()
    logger.info(f'Defined remote: {remote} connectionStatus: {connectionOk}')

    if connectionOk:
        remote.updateBackupInfo()

    for path, backup in remote.getBackupInfo():
        created = datetime.datetime.fromtimestamp(backup.created)
        volumeInfo    = [f'    - {v.name} ({v.size*1e-6:.2f} MB)' for v in backup.volumes]
        volumeInfoStr = '\n'.join(volumeInfo)
        logger.info(f"  Found backup file {path} from {created} with volumes\n{volumeInfoStr}")
    

backupInfo = dockerHelper.getBackupList()

logger.info(f"Detected volumes")
for v in backupInfo:
    logger.info(f'  - [{"x" if v.shouldRun else " "}] {v.volume.name}')

    for c in v.containers:
        logger.info(f'    - [{"x" if c.shouldStop else " "}] {c.container.name}')



schedule.every(3).days.at("02:00").do(backupWorker.DoBackup)

if configHelper.getConfig().initialRun:
    BackupWorker().DoBackup()

while True:
    schedule.run_pending()
    time.sleep(1)