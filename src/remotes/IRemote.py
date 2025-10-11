from enum import StrEnum
from abc import ABC, abstractmethod

from pathlib import Path

from definitions.backupMeta import BackupMeta


class IRemote(ABC):
    @abstractmethod
    def getDescriptor(self) -> str:
        ...

    @abstractmethod
    def testConnection(self) -> bool:
        ...

    @abstractmethod
    def updateBackupInfo(self) -> None:
        ...

    @abstractmethod
    def getBackupInfo(self) -> list[tuple[Path, BackupMeta]]:
        ...

    @abstractmethod
    def saveBackup(self, source: Path) -> bool:
        ...

    @abstractmethod
    def deleteBackup(self, path: BackupMeta) -> bool:
        ...

    
    


