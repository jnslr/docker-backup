import logging
import paramiko

from pathlib import Path


from .IRemote import IRemote

from definitions.backupMeta import BackupMeta
from dacite import from_dict

class SftpRemote(IRemote):

    def __init__(self):
        self.m_logger = logging.getLogger(__name__)

        self.m_host   = None
        self.m_port   = None
        self.m_user   = None
        self.m_pass   = None
        self.m_targetDir:Path = None

    def __str__(self):
        return f'SftpRemote: {self.m_user}@{self.m_host}:{self.m_port} --> {self.m_targetDir}'
    
    def setConnection(self, host:str, port:int, user:str, password:str):
        self.m_host = host
        self.m_port = int(port)
        self.m_user = user
        self.m_pass = password

    def setTargetDir(self, targetDir:str):
        self.m_targetDir = Path(targetDir)

    def connect(self) -> paramiko.SFTPClient:
        transport = paramiko.Transport((self.m_host, self.m_port))
        transport.connect(username = self.m_user, password = self.m_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        self.m_logger.info(f"Connected via sftp to {self.m_host}")
        return sftp
    
    def disconnect(self, client: paramiko.SFTPClient):
        client.close()

    def createTargetDir(self, client: paramiko.SFTPClient):
        #Emulate mkdir -p
        for dir in self.m_targetDir.parts:
            try:
                client.chdir(str(dir))
            except IOError:
                client.mkdir(str(dir))


    # Interface Methods of IRemote

    def testConnection(self) -> bool:
        try:
            sftpClient = self.connect()
            sftpClient.close()
        except Exception as e:
            self.m_logger.warning(f'Connection to {self} failed: {e}')
            return False
        return True

    def saveBackup(self, source: Path) -> bool:
        try:
            sftpClient = self.connect()
            self.createTargetDir(sftpClient)

            target = self.m_targetDir.joinpath(source.name)
            sftpClient.put( str(source), str(target))
            sftpClient.close()
        except Exception as e:
            self.m_logger.warning(f'Saving {source} failed: {e}')
            return False
        
        self.m_logger.warning(f'Saving {source} to {self.m_targetDir}')
        return True
    
    def getBackups(self) -> list[tuple[Path, BackupMeta]]:
        backupInfos = []

        try:
            sftpClient = self.connect()
            sftpClient.chdir(self.m_targetDir.as_posix())
            
            backupFiles = sftpClient.listdir('')
            backupFiles = [f for f in backupFiles if f.endswith('.zip')]
            

            for backupFile in backupFiles:
                backupPath = self.m_targetDir.joinpath(backupFile)
                with sftpClient.file(backupFile, mode='r') as f:
                    backupInfo = BackupMeta.fromFile(f)
                    backupInfos.append( (backupPath, backupInfo))
            sftpClient.close()
        except Exception as e:
            self.m_logger.warning(f'Could not get backups: {e}')

        return backupInfos

    def deleteBackup(self, path: Path) -> bool:
        try:
            sftpClient = self.connect()
            sftpClient.remove(path.as_posix())
            sftpClient.close()
        except Exception as e:
            self.m_logger.warning(f'Delete {path} failed: {e}')
            return False
        
        self.m_logger.warning(f'Deleted {path}')
        return True