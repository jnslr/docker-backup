import re
import logging

from docker import DockerClient
from docker.models.volumes    import Volume
from docker.models.containers import Container

from config.config import ConfigHelper
from definitions.backupList import VolumeBackupInfo, ContainerBackupInfo

class DockerHelper:
    _instance = None
    def __new__(cls, *args, **kwds):
        if cls._instance is None:
            cls._instance = super(DockerHelper, cls).__new__(cls)
            cls._instance.init()
        return cls._instance
    
    def init(self):
        self.m_logger = logging.getLogger(__name__)
        self.m_client = DockerClient.from_env()

        self.m_volumeList:    list[Volume]    = []
        self.m_containerList: list[Container] = []

    def startContainer(self, container:Container) -> bool:
        self.m_logger.info(f"Starting container {container.name} {container.id}")
        container.start()

    def stopContainer(self,container:Container) -> bool:
        self.m_logger.info(f"Stopping container {container.name} {container.id} (status: {container.status})")
        containerRunning = container.status=='running'
        if containerRunning:
            container.stop()
        return containerRunning
    
    def getVolumes(self) -> list[Volume]:
        return self.m_client.volumes.list()
    
    def getContainers(self) -> list[Container]:
        return self.m_client.containers.list(all=True)
    
    def updateDockerInfo(self):
        self.m_containerList = self.getContainers()
        self.m_volumeList    = self.getVolumes()
    
    def isVolumeIncluded(self, volume: Volume ) -> bool:
        config = ConfigHelper().getConfig()
        includeList = config.volumes.include
        excludeList = config.volumes.exclude

        for excludePattern in excludeList:
            if re.match(excludePattern, volume.name) is not None:
                self.m_logger.debug(f"Volume {volume.name} is excluded as it matches exclude pattern {excludePattern}")
                return False
            
        for includePattern in includeList:
            if re.match(includePattern, volume.name) is not None:
                self.m_logger.debug(f"Volume {volume.name} is included as it matches include pattern {includePattern}")
                return True

        self.m_logger.debug(f"Volume {volume.name} is excluded as it does not match any include pattern")
        return False
    
    def isContainerStoppable(self, container: Container ) -> bool:
        config = ConfigHelper().getConfig()
        noStopList = config.volumes.containerNoStop
        
        for noStopPattern in noStopList:
            if re.match(noStopPattern, container.name) is not None:
                self.m_logger.debug(f"Container {container.name} is not stopped as it matches no stop pattern {noStopPattern}")
                return False
        
        return True

    def getContainersUsedByVolume(self, volume:Volume) -> list[Container]:
        containersUsingVolume = [ ]
        for container in self.m_containerList:
            mounts = container.attrs.get('Mounts')
            if any([m for m in mounts if m.get('Name')==volume.name]):
                containersUsingVolume.append(container)
        return containersUsingVolume
    
    def getBackupList(self) -> list[VolumeBackupInfo]:
        self.updateDockerInfo()
        
        backupInfo = []
        
        for volume in self.m_volumeList:
            volumeBackupInfo = VolumeBackupInfo(volume=volume, shouldRun=self.isVolumeIncluded(volume))
            for container in self.getContainersUsedByVolume(volume):
                containerInfo = ContainerBackupInfo(container=container, shouldStop= self.isContainerStoppable(container))
                volumeBackupInfo.containers.append(containerInfo)
            backupInfo.append(volumeBackupInfo)
        return backupInfo
