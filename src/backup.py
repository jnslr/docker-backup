import re
import os
import json
import time
import shutil
import paramiko

from typing import Self
from dacite import from_dict
from zipfile import ZipFile
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from docker import DockerClient
from docker.models.volumes    import Volume
from docker.models.containers import Container

# Local imports
from logger import logger, printHeader,printLine
from definitions import BackupInfo, VolumeBackupInfo, BackupHistory, AppSettings, VolumeInfo
from settings import loadSettings, saveSettings, loadBackupHistory
from selfContainerDetect import detectSelfContainer


#Settings
DRYRUN = False
excludeList  = []
includeList  = []
dontStopList = []

VOLUMES_EXCLUDE = os.getenv('VOLUMES_EXCLUDE')
if VOLUMES_EXCLUDE is not None:
    excludeList = VOLUMES_EXCLUDE.split(',')

VOLUMES_INCLUDE = os.getenv('VOLUMES_INCLUDE')
if VOLUMES_INCLUDE is not None:
    includeList = VOLUMES_INCLUDE.split(',')

CONTAINER_NOSTOP = os.getenv('CONTAINER_NOSTOP')
if CONTAINER_NOSTOP is not None:
    dontStopList = CONTAINER_NOSTOP.split(',')

KEEP_BACKUPS = int(os.getenv('KEEP_BACKUPS',5))


SFTP_TARGET = os.getenv('SFTP_TARGET')
SFTP_HOST   = os.getenv('SFTP_HOST')
SFTP_USER   = os.getenv('SFTP_USER')
SFTP_PORT   = int(os.getenv('SFTP_PORT','22'))
SFTP_PASS   = os.getenv('SFTP_PASS')

ZIP_FORMAT  = 'zip' #gztar

settings = loadSettings()
history  = loadBackupHistory()

class BackupCreator():
    _instance = None
       
    @classmethod
    def getInstance(cls) -> Self:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.reloadSettings()
        self.m_history      = loadBackupHistory()
        self.m_dockerClient = DockerClient.from_env()
    
    def getHistory(self) -> BackupHistory:
        return self.m_history
    
    def getSettings(self) -> AppSettings:
        return self.m_settings
    
    def reloadSettings(self) -> None:
        self.m_settings = loadSettings()
    
    def updateSettings(self, newSettings:AppSettings) -> None:
        saveSettings(newSettings)
        self.reloadSettings()        

    def getVolumes(self) -> list[VolumeInfo]:
        allContainers = self.m_dockerClient.containers.list()
        res = []
        for volume in self.m_dockerClient.volumes.list():           
            res.append(VolumeInfo(
                name = volume.name,
                usedByContainers=[c.name for c in findContainersUsedByVolume(volume,allContainers)]
                
            ))
        return res


# dockerClient = 
#     allContainers     = dockerClient.containers.list(all=True)
#     runningContainers = [c for c in allContainers if c.status=='running']
#     allVolumes    = dockerClient.volumes.list()


if __name__=='__main__':
    from server import startServer
    start = time.time()
    printHeader()
    logger.info(f"Docker Backup service started")
    printHeader()


    selfContainer = detectSelfContainer()

    t = startServer()
    t.join()
    exit()




def filterVolumes(volumeList:Volume, includeFilter:list[str], excludeFilter:list[str]) -> list[Volume]:
    def filterByExclude(v:Volume):
        excludeMatches = [excludePattern for excludePattern in excludeList if re.match(excludePattern, v.name)]
        excludeVolume = any(excludeMatches)
        if excludeMatches:
            logger.info(f"Volume {v.name} is excluded as it matches exclude patterns {excludeMatches}")
        return not excludeVolume

    def filterByInclude(v:Volume):
        includeMatches = [includePattern for includePattern in includeList if re.match(includePattern, v.name)]
        includeVolume = any(includeMatches)
        if not includeVolume:
            logger.info(f"Volume {v.name} is excluded as does not match any include pattern {includeList}")
        return includeVolume

    res = list(filter(filterByExclude, volumeList))
    res = list(filter(filterByInclude, res))
    return res

def findContainersUsedByVolume(volume:Volume,containerList:list[Container]) -> list[Container]:
    containersUsingVolume = [ ]
    for container in containerList:
        mounts = container.attrs.get('Mounts')
        if any([m for m in mounts if m.get('Name')==volume.name]):
            containersUsingVolume.append(container)
    return containersUsingVolume

def stopContainer(container:Container) -> bool:
    """Stop container and return if the container was running before"""
    logger.info(f"Stopping container {container.name} {container.id}")
    dontStopMatches = [noStopPattern for noStopPattern in dontStopList if re.match(noStopPattern, container.name)]
    dontStop = any(dontStopMatches)
    if dontStop:
        logger.info(f"Container not stopped as it is included in no-stop list")
        return False
    containerRunning = container.status=='running'
    if not DRYRUN and containerRunning:
        container.stop()
    return containerRunning

def startContainer(container:Container) -> bool:
    """Start container and return if the container was running before"""
    logger.info(f"Starting container {container.name} {container.id}")
    if not DRYRUN:
        container.start()

def backupVolume(volume:Volume, backupDir: Path) -> VolumeBackupInfo:
    logger.info(f"Performing backup for volume {volume.name}")
    infoPath   = backupDir.joinpath(f'{volume.name}.json')
    dstPath    = backupDir.joinpath(volume.name)
    srcPath    = Path(volume.attrs.get('Mountpoint'))
    volumeSize = sum(p.stat().st_size for p in srcPath.rglob('*'))
    volumeInfo = VolumeBackupInfo(
        name = volume.name,
        volumeAttributes=volume.attrs,
        created=time.time(),
        srcPath=str(srcPath),
        dstPath=str(dstPath),
        relDstPath=str(os.path.relpath(dstPath,infoPath.parent)),
        size=volumeSize
    )
    volumeArchive = Path(shutil.make_archive(dstPath, ZIP_FORMAT, '/', srcPath))
    logger.info(f"Backup archived to {volumeArchive}. Original size: {volumeSize}. Compressed size: {volumeArchive.stat().st_size}")
    #shutil.copytree(srcPath,dstPath)
    return volumeInfo

def copyViaSftp( src:Path, dst:Path ):
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username = SFTP_USER, password = SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    logger.info(f"Connected via sftp to {SFTP_HOST}")
    
    #Emulate mkdir -p
    for dir in reversed(dst.parents):
        try:
            sftp.chdir(str(dir))
        except IOError:
            sftp.mkdir(str(dir))
    
    sftp.put( str(src), str(dst) )
    sftp.close()

def deleteOldBackups( keep:int ):
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username = SFTP_USER, password = SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    logger.info(f"Connected via sftp to {SFTP_HOST}")
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
                    created = datetime.fromtimestamp(backupInfo.created)
                    volumeInfo = [f'{v.name} ({v.size})' for v in backupInfo.volumes]
                    logger.info(f"Found backup file from {created} with volumes {volumeInfo}")
                except Exception as e:
                    logger.error(f"Failed to determine backup info for {backupFile}. Error {e}")
    backupInfos.sort(key=lambda i: i.created)
    for backup in backupInfos[:-keep]:
        logger.info(f"Deleting old backup {backup.file} (as we only want to keep the latest {keep})")
        sftp.remove(backup.file)


def runBackup():
    tmpBackupDir = Path(__file__).parent.joinpath('Backup')
    if tmpBackupDir.exists():
        shutil.rmtree(tmpBackupDir)
    tmpBackupDir.mkdir(exist_ok=True)
    dockerClient = DockerClient.from_env()
    allContainers     = dockerClient.containers.list(all=True)
    runningContainers = [c for c in allContainers if c.status=='running']
    allVolumes    = dockerClient.volumes.list()

    backupInfo = BackupInfo()

    filteredVolumes = filterVolumes(allVolumes,includeList,excludeList)
    logger.info(f"Performing backup on filtered volumes {filteredVolumes}")
    for volume in filteredVolumes:
        logger.info(f"----------------------------------------------------------------------")
        logger.info(f"Starting Backup for volume {volume.name}")
        logger.info(f"Volume is used by containers:")
        stoppedContainers = []
        for container in findContainersUsedByVolume(volume,allContainers):
            logger.info(f"  - {container.name} (status: {container.status})")
            if stopContainer(container):
                stoppedContainers.append(container)
        logger.info(f"{len(stoppedContainers)} containers have been stopped")
        try:
            volumeInfo = backupVolume(volume, tmpBackupDir)
            backupInfo.volumes.append(volumeInfo)
        except Exception as e:
            logger.error(f"Error backing up volume {volume.name}: {e}")
        for container in stoppedContainers:
            startContainer(container)

    infoPath = tmpBackupDir.joinpath('backupInfo.json')
    infoPath.write_text(json.dumps(asdict(backupInfo), indent=4))
    logger.info(f"Backup info written to {infoPath}")

    archiveName = datetime.now().strftime("%y%m%d-%H%M%S-Backup")
    logger.info(f"Create Backup archive {archiveName}")
    backupArchive = Path(shutil.make_archive(archiveName, ZIP_FORMAT, tmpBackupDir, ''))
    shutil.rmtree(tmpBackupDir)

    sftpTarget = Path(SFTP_TARGET).joinpath(backupArchive.name)
    copyViaSftp(backupArchive, sftpTarget)

    logger.info(f"Cleaning old backups")
    deleteOldBackups(KEEP_BACKUPS)

    runningContainersAfterBackup = [c for c in dockerClient.containers.list(all=True) if c.status=='running']
    logger.info(f"Backup finished. Took {int(time.time()-start)} seconds. Running containers {len(runningContainersAfterBackup)}/{len(runningContainers)}")
