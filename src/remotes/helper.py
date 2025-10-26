import logging

from definitions.backupConfig import SftpRemoteConfig
from config.config import ConfigHelper

from .IRemote    import IRemote
from .sftpRemote import SftpRemote


class RemoteHelper:
    _instance = None
    def __new__(cls, *args, **kwds):
        if cls._instance is None:
            cls._instance = super(RemoteHelper, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.m_logger = logging.getLogger(__name__)
        self.m_remotes = []

        self.updateRemotes()

    def updateRemotes(self):
        self.m_remotes.clear()

        remoteConfig = ConfigHelper().getConfig().remotes

        for remoteConfig in remoteConfig:
            if isinstance(remoteConfig, SftpRemoteConfig):
                self.addSftpRemote(remoteConfig)

    def addSftpRemote(self, config: SftpRemoteConfig):
        remote = SftpRemote()
        remote.setConnection(
            host= config.host,
            port=config.port,
            user= config.user,
            password=config.password)
        remote.setTargetDir(config.targetDirectory)
        
        self.m_remotes.append(remote)

    def getRemotes(self) -> list[IRemote]:
        return self.m_remotes
        
        
