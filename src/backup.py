import re
import os
import json
import time
import shutil
import logging
import paramiko
import logging.handlers

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from docker import DockerClient
from docker.models.volumes    import Volume
from docker.models.containers import Container

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


SFTP_TARGET = os.getenv('SFTP_TARGET')
SFTP_HOST   = os.getenv('SFTP_HOST')
SFTP_USER   = os.getenv('SFTP_USER')
SFTP_PORT   = int(os.getenv('SFTP_PORT','22'))
SFTP_PASS   = os.getenv('SFTP_PASS')

logger = logging.getLogger("PythonBackup")
fmt    = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
ch     = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

start = time.time()
logger.info(f"######################################################################")
logger.info(f"Docker Backup service started")
logger.info(f"######################################################################")


@dataclass
class BackupInfo:
    volumeAttributes:dict
    created:    float
    srcPath:    str
    dstPath:    str
    relDstPath: str

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

def backupVolume(volume:Volume, backupDir: Path):
    logger.info(f"Performing backup for volume {volume.name}")
    infoPath = backupDir.joinpath(f'{volume.name}.json')
    dstPath  = backupDir.joinpath(volume.name)
    srcPath  = volume.attrs.get('Mountpoint')
    backupInfo = BackupInfo(
        volumeAttributes=volume.attrs,
        created=time.time(),
        srcPath=srcPath,
        dstPath=str(dstPath),
        relDstPath=str(os.path.relpath(dstPath,infoPath.parent))
    )
    infoPath.write_text(json.dumps(asdict(backupInfo), indent=4))
    logger.info(f"Backup info written to {infoPath}")
    shutil.copytree(srcPath,dstPath)

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

def runBackup():
    tmpBackupDir = Path(__file__).parent.joinpath('Backup')
    if tmpBackupDir.exists():
        shutil.rmtree(tmpBackupDir)
    tmpBackupDir.mkdir(exist_ok=True)
    dockerClient = DockerClient.from_env()
    allContainers     = dockerClient.containers.list(all=True)
    runningContainers = [c for c in allContainers if c.status=='running']
    allVolumes    = dockerClient.volumes.list()

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
            backupVolume(volume, tmpBackupDir)
        except Exception as e:
            logger.error(f"Error backing up volume {volume.name}: {e}")
        for container in stoppedContainers:
            startContainer(container)

    archiveName = datetime.now().strftime("%y%m%d-%H%M%S-Backup")
    logger.info(f"Create Backup archive {archiveName}")
    backupArchive = Path(shutil.make_archive(archiveName, 'gztar', tmpBackupDir, ''))
    shutil.rmtree(tmpBackupDir)

    sftpTarget = Path(SFTP_TARGET).joinpath(backupArchive.name)
    copyViaSftp(backupArchive, sftpTarget)


    runningContainersAfterBackup = [c for c in dockerClient.containers.list(all=True) if c.status=='running']
    logger.info(f"Backup finished. Took {int(time.time()-start)} seconds. Running containers {len(runningContainersAfterBackup)}/{len(runningContainers)}")
