#pip install python-dotenv
import os
import datetime
import json
from dacite import from_dict

from zipfile import ZipFile
import tarfile
import paramiko

from backup import BackupInfo
from backup import logger
from dotenv import load_dotenv

load_dotenv()

SFTP_TARGET = os.getenv('SFTP_TARGET')
SFTP_HOST   = os.getenv('SFTP_HOST')
SFTP_USER   = os.getenv('SFTP_USER')
SFTP_PORT   = int(os.getenv('SFTP_PORT','22'))
SFTP_PASS   = os.getenv('SFTP_PASS')

print(SFTP_HOST)

transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
transport.connect(username = SFTP_USER, password = SFTP_PASS)
sftp = paramiko.SFTPClient.from_transport(transport)
logger.info(f"Connected via sftp to {SFTP_HOST}")



#sftp.listdir_attr
sftp.chdir(SFTP_TARGET)
backupFiles = sftp.listdir('')
backupFiles = [f for f in backupFiles if f.endswith('.zip')]
backupInfos = []
for backupFile in backupFiles:
    with sftp.file(backupFile, mode='r') as f:
        with ZipFile(f,'r') as zf:
            fileList = zf.filelist
            try:
                zipInfo = [f for f in fileList if f.filename=='backupInfo.json'][0]
                backupInfo = from_dict(data_class=BackupInfo, data=json.loads(zf.read(zipInfo)) )
                backupInfo.file = backupFile
                backupInfos.append(backupInfo)
                created = datetime.datetime.fromtimestamp(backupInfo.created)
                volumeInfo = [f'{v.name} ({v.size})' for v in backupInfo.volumes]
                logger.info(f"Found backup file from {created} with volumes {volumeInfo}")
            except Exception as e:
                logger.error(f"Failed to determine backup info for {backupFile}")

backupInfos.sort(key=lambda i: i.created)
for backup in backupInfos[:-5]:
    logger.info(f"Deleting old backup {backup.file} (as we only want to keep the lastest 5)")
    sftp.remove(backup.file)







# for file in files:
#     attributes = sftp.lstat(file)

