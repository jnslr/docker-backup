import logging

from pathlib import Path
from threading import Thread, Event

from .helper import BackupHelper
from remotes.helper import RemoteHelper
from dockerHelper.helper import DockerHelper
from config.config import ConfigHelper
from definitions.backupState import BackupState, State

class BackupWorker():
    _instance = None
    def __new__(cls, *args, **kwds):
        if cls._instance is None:
            cls._instance = super(BackupWorker, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.m_logger = logging.getLogger(__name__)

        self.m_backupHelper  = BackupHelper()
        self.m_remoteHelper  = RemoteHelper()
        self.m_dockerHelper  = DockerHelper()
        self.m_configHelper  = ConfigHelper()
        self.m_state         = BackupState()
        
        self.m_runEvent = Event()
        self.m_thread = Thread(target=self.Run, daemon=True, name="BackupWorker")
        self.m_thread.start()

    def Run(self):
        self.m_logger.info("Backup worker thread started")
        while True:
            self.m_runEvent.wait()
            self.m_logger.info("Backup worker thread: StartBackup")
            self.DoBackup()
            self.m_runEvent.clear()

    def StartBackup(self):
        self.m_runEvent.set()

    def DoBackup(self):
        backupList = self.m_dockerHelper.getBackupList()
        backupPath = self.m_backupHelper.createBackup(backupList)

        self.m_state.state = State.BACKUP_TRANSFER
        self.SaveBackupToRemotes(backupPath)
        self.CleanRemotes()
        self.m_backupHelper.cleanTmpDir()
        self.m_state.state = State.IDLE

    def SaveBackupToRemotes(self,backupPath: Path):
        for remote in self.m_remoteHelper.getRemotes():
            remote.saveBackup(backupPath)

    def CleanRemotes(self):
        keepCount = self.m_configHelper.getConfig().keepCount

        for remote in self.m_remoteHelper.getRemotes():
            self.m_state.currentRemote = str(remote)
            remote.updateBackupInfo()
            remoteBackups = remote.getBackupInfo()
            remoteBackups.sort(key=lambda i: i[1].created)
            for path, _ in remoteBackups[:-keepCount]:
                remote.deleteBackup(path)
            remote.updateBackupInfo()
        self.m_state.currentRemote = None