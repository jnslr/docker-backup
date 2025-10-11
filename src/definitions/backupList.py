from dataclasses import dataclass, field

from docker.models.volumes    import Volume
from docker.models.containers import Container

@dataclass
class ContainerBackupInfo:
    shouldStop: bool
    container: Container

@dataclass
class VolumeBackupInfo:
    shouldRun:  bool
    volume:     Volume
    containers: list[ContainerBackupInfo] = field(default_factory=list)
