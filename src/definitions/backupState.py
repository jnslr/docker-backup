from enum import StrEnum
from dataclasses import dataclass, field

class State(StrEnum):
    IDLE                   = "IDLE"
    BACKUP_COMPRESS_VOLUME = "BACKUP_VOLUME"
    BACKUP_CREATE_FILE     = "BACKUP_CREATE_FILE"
    BACKUP_TRANSFER        = "BACKUP_TRANSFER"

@dataclass
class BackupState:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    state: State              = field(default=State.IDLE)
    lastStart: float          = field(default=None)
    lastDuration: float       = field(default=None)
    currentVolume: str        = field(default=None)
    currentVolumeProgress:int = field(default=None)
    currentRemote: str        = field(default=None)