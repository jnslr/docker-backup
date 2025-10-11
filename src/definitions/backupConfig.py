from dataclasses import dataclass, field

@dataclass
class SftpRemoteConfig:
    host: str
    port: int
    user: str
    password: str
    targetDirectory: str

@dataclass
class VolumeConfig:
    include:         list[str] = field(default_factory=lambda: ['.*'])
    exclude:         list[str] = field(default_factory=list)
    containerNoStop: list[str] = field(default_factory=list)

@dataclass
class BackupConfig:
    initialRun: bool                = False
    keepCount:  int                 = 5
    volumes: VolumeConfig           = field(default_factory=VolumeConfig)
    remotes: list[SftpRemoteConfig] = field(default_factory=list)

