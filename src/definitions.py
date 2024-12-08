import time
from dataclasses import dataclass,field

@dataclass
class VolumeBackupInfo:
    name:       str
    volumeAttributes:dict
    created:    float
    srcPath:    str
    dstPath:    str
    relDstPath: str
    size:       int

@dataclass
class BackupInfo:
    created: float            = field(default_factory=time.time)
    volumes: list[VolumeBackupInfo] = field(default_factory=list)

@dataclass
class BackupHistory:
    backupList: list[BackupInfo] = field(default_factory=list)


@dataclass
class ContainerBackupSettings:
    containerName: str
    stopContainerOnBackup: bool = True

@dataclass
class VolumeBackupSettings:
    volumeName: str
    includePaths: list[str] = field(default_factory=lambda: list(["**/*"])) #Glob expresions for included paths

@dataclass
class BackupSettings:
    """Contains setting for a single backup"""
    cronSetting:       str
    volumeSettings:    list[VolumeBackupSettings]    = field(default_factory=list)
    containerSettings: list[ContainerBackupSettings] = field(default_factory=list)
    
@dataclass
class AppSettings:
    """Contains the whole applications setting"""
    backups: list[BackupSettings] = field(default_factory=list)


@dataclass
class VolumeInfo:
    "Info about a volume"
    name: str
    usedByContainers: list[str]



