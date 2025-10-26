import logging
import time
import os
import shutil
import json
import datetime

from pathlib import Path
from dataclasses import asdict
from datetime import datetime

from docker.models.volumes    import Volume
from docker.models.containers import Container

from dockerHelper.helper import DockerHelper
from definitions.backupList import VolumeBackupInfo
from definitions.backupMeta import BackupMeta, VolumeMeta

class BackupHelper:

    def __init__(self):
        self.m_logger       = logging.getLogger(__name__)
        self.m_dockerHelper = DockerHelper()

        self.m_zipFormat    = 'zip' #gztar
        self.m_tmpDir       = Path(__file__).parent.parent.joinpath('tmp')
        self.m_tmpBackupDir = self.m_tmpDir.joinpath('backup')

    def cleanTmpBackupDir(self):
        if self.m_tmpBackupDir.exists():
            shutil.rmtree(self.m_tmpBackupDir)

    def cleanTmpDir(self):
        if self.m_tmpDir.exists():
            shutil.rmtree(self.m_tmpDir)

    def createBackup(self, volumeList: list[VolumeBackupInfo]) -> Path:
        self.m_logger.info(f"Starting backup worker")
        backupStart = time.time()


        self.cleanTmpBackupDir()
        self.m_tmpBackupDir.mkdir(exist_ok=True, parents=True)

        volumesToProcess = [v for v in volumeList if v.shouldRun]

        backupMeta = BackupMeta()

        for v in volumesToProcess:
            self.stopContainersUsedByVolume(v)
            volumeMeta = self.processVolumeBackup(v)
            backupMeta.volumes.append(volumeMeta)

        self.writeBackupMetadata(backupMeta)
        backupPath = self.compressBackup()
        self.cleanTmpBackupDir()

        durationS = time.time()-backupStart
        self.m_logger.info(f"Local backup created: {backupPath.name} took {durationS:.2f} seconds")

        return backupPath

    def writeBackupMetadata(self, backupMeta:BackupMeta):
        metaPath = self.m_tmpBackupDir.joinpath('backupInfo.json')
        metaPath.write_text(json.dumps(asdict(backupMeta), indent=4))
        self.m_logger.info(f"Backup info written to {metaPath}")

    def compressBackup(self) -> Path:
        archiveName = datetime.now().strftime("%y%m%d-%H%M%S-Backup")
        archivePath = self.m_tmpDir.joinpath(archiveName)
        self.m_logger.info(f"Create Backup archive {archiveName}")

        archivePath = shutil.make_archive(archivePath, self.m_zipFormat, self.m_tmpBackupDir, '')
        return Path(archivePath)

    def processVolumeBackup(self, backupVolume: VolumeBackupInfo) -> VolumeMeta:
        self.m_logger.info(f"Starting Backup for volume {backupVolume.volume.name}")
        volumeBackupStart = time.time()
        
        volumeMeta = None
        stoppedContainers = self.stopContainersUsedByVolume(backupVolume)
        try:
            volumeMeta = self.compressVolumeToTmpBackupDir(backupVolume.volume)
        except Exception as e:
            self.m_logger.error(f"Error backing up volume {backupVolume.volume.name}: {e}")
        
        for container in stoppedContainers:
            self.m_dockerHelper.startContainer(container)

        volumeBackupDuration = time.time() - volumeBackupStart
        self.m_logger.info(f"Volume backup completed for {backupVolume.volume.name}: took {volumeBackupDuration:.2f} seconds")
        
        return volumeMeta
        
    def stopContainersUsedByVolume(self, backupVolume: VolumeBackupInfo) -> list[Container]:
        stoppedContainers = []
        for c in backupVolume.containers:
            if not c.shouldStop:
                continue
            if self.m_dockerHelper.stopContainer(c.container):
                stoppedContainers.append(c.container)

        self.m_logger.info(f"{len(stoppedContainers)} containers have been stopped")
        return stoppedContainers
    
    def compressVolumeToTmpBackupDir(self, volume:Volume) -> VolumeMeta:
        self.m_logger.info(f"Performing backup for volume {volume.name}")
        infoPath   = self.m_tmpBackupDir.joinpath(f'{volume.name}.json')
        dstPath    = self.m_tmpBackupDir.joinpath(volume.name)
        srcPath    = Path(volume.attrs.get('Mountpoint'))

        volumeMeta = VolumeMeta(
            name = volume.name,
            volumeAttributes=volume.attrs,
            created=time.time(),
            srcPath=str(srcPath),
            dstPath=str(dstPath),
            relDstPath=str(os.path.relpath(dstPath,infoPath.parent)),
            size=0,
            error=None
        )
        try:
            volumeMeta.size = sum(p.stat().st_size for p in srcPath.rglob('*'))
            volumeArchive = Path(shutil.make_archive(dstPath, self.m_zipFormat, '/', srcPath))
            self.m_logger.info(f"Backup archived to {volumeArchive}. Original size: {volumeMeta.size}. Compressed size: {volumeArchive.stat().st_size}")
        except Exception as e:
            self.m_logger.warning(f"Failed to backup {volume.name}: {e}")
            volumeMeta.error = str(e)
        
        return volumeMeta


            






