import time
import json

from zipfile     import ZipFile
from dataclasses import dataclass, field
from dacite      import from_dict



@dataclass
class VolumeMeta:
    name:             str
    volumeAttributes: dict
    created:          float
    srcPath:          str
    dstPath:          str
    relDstPath:       str
    size:             int
    error:            str|None

@dataclass
class BackupMeta:
    created: float            = field(default_factory=time.time)
    volumes: list[VolumeMeta] = field(default_factory=list)

    @staticmethod
    def fromFile(file):
        with ZipFile(file,'r') as zf:
            fileList = zf.filelist
            try:
                zipInfo = [f for f in fileList if f.filename=='backupInfo.json'][0]
                backupInfo = from_dict(data_class=BackupMeta, data=json.loads(zf.read(zipInfo)) )
                return backupInfo
            except Exception as e:
                return None
