from abc import ABC, abstractmethod

from pathlib import Path

from definitions.backupMeta import BackupMeta

class IRemote(ABC):
    
    @abstractmethod
    def testConnection(self) -> bool:
        ...

    @abstractmethod
    def getBackups(self) -> list[tuple[Path, BackupMeta]]:
        ...

    @abstractmethod
    def saveBackup(self, source: Path) -> bool:
        ...

    @abstractmethod
    def deleteBackup(self, path: BackupMeta) -> bool:
        ...

    
    


