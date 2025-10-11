from pathlib import Path

from .helper import BackupHelper
from remotes.helper import RemoteHelper
from dockerHelper.helper import DockerHelper
from config.config import ConfigHelper

class BackupWorker():
    def __init__(self):
        self.m_backupHelper  = BackupHelper()
        self.m_remoteHelper  = RemoteHelper()
        self.m_dockerHelper  = DockerHelper()
        self.m_configHelper  = ConfigHelper()


    def DoBackup(self):
        backupList = self.m_dockerHelper.getBackupList()
        backupPath = self.m_backupHelper.createBackup(backupList)
        self.SaveBackupToRemotes(backupPath)
        self.CleanRemotes()
        self.m_backupHelper.cleanTmpDir()

    def SaveBackupToRemotes(self,backupPath: Path):
        for remote in self.m_remoteHelper.getRemotes():
            remote.saveBackup(backupPath)

    def CleanRemotes(self):
        keepCount = self.m_configHelper.getConfig().keepCount

        for remote in self.m_remoteHelper.getRemotes():
            remoteBackups = remote.getBackups()
            remoteBackups.sort(key=lambda i: i[1].created)
            for path, _ in remoteBackups[:-keepCount]:
                remote.deleteBackup(path)