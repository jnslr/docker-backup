import os
import logging

from definitions.backupConfig import BackupConfig, SftpRemoteConfig

class ConfigHelper():
    _instance = None
    def __new__(cls, *args, **kwds):
        if cls._instance is None:
            cls._instance = super(ConfigHelper, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.m_logger = logging.getLogger(__name__)
        self.m_config = BackupConfig()

        self.loadConfigFromEnv()
        
        self.m_logger.info(f'Loaded config: {self.m_config}')

    def loadConfigFromEnv(self):
        initialRunFromEnv      = os.getenv('INITIAL_RUN') 
        keepBackupsFromEnv     = os.getenv('KEEP_BACKUPS') 
        volumeIncludeFromEnv   = os.getenv('VOLUMES_INCLUDE')
        volumeExcludeFromEnv   = os.getenv('VOLUMES_EXCLUDE')
        containerNoStopFromEnv = os.getenv('CONTAINER_NOSTOP')

        if initialRunFromEnv is not None and initialRunFromEnv.lower() == 'true':
            self.m_config.initialRun = True

        if keepBackupsFromEnv is not None:
            self.m_config.keepCount = int(keepBackupsFromEnv)

        if volumeIncludeFromEnv is not None:
            self.m_config.volumes.include = volumeIncludeFromEnv.split(',')
        
        if volumeExcludeFromEnv is not None:
            self.m_config.volumes.exclude = volumeExcludeFromEnv.split(',')
        
        if containerNoStopFromEnv is not None:
            self.m_config.volumes.containerNoStop = containerNoStopFromEnv.split(',')

        sftpHostFromEnv = os.getenv('SFTP_HOST')
        sftpPortFromEnv = os.getenv('SFTP_PORT')
        sftpUserFromEnv = os.getenv('SFTP_USER')
        sftpPassFromEnv = os.getenv('SFTP_PASS')
        sftpDirFromEnv  = os.getenv('SFTP_TARGET')

        sftpRemote = SftpRemoteConfig(
            host=sftpHostFromEnv,
            port=sftpPortFromEnv,
            user=sftpUserFromEnv,
            password=sftpPassFromEnv,
            targetDirectory=sftpDirFromEnv
        )

        self.m_config.remotes.append(sftpRemote)

    def getConfig(self) -> BackupConfig:
        return self.m_config
    