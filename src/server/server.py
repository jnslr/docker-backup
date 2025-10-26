import uvicorn
import threading
import logging

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.config import ConfigHelper
from dockerHelper.helper import DockerHelper
from remotes.helper import RemoteHelper

from definitions.backupConfig import BackupConfig

class Server():
    def __init__(self):
        self.m_logger = logging.getLogger(__name__)
        self.m_thread = None
        self.m_app = FastAPI()

        self.m_config = ConfigHelper()
        self.m_docker = DockerHelper()
        self.m_remote = RemoteHelper()

        
        self.m_staticDir = Path(__file__).parent.joinpath('static')
        self.m_logDir    = Path(__file__).parent.parent.joinpath('log')
        self.addRoutes()

        self.m_logger.info('Server initialized')

    def startServer(self):
        uvicornArgs ={'host':'0.0.0.0','port':80}
        self.m_thread = threading.Thread(target=uvicorn.run, args=[self.m_app],kwargs=uvicornArgs,  name='ServerThread', daemon=True)
        self.m_thread.start()

        self.m_logger.info('Server thread started')

    def addRoutes(self) -> BackupConfig:
        @self.m_app.get("/api/config")
        def getConfig():
            return self.m_config.getConfig()

        @self.m_app.get("/api/log")
        def getConfig():
            logFiles = self.m_logDir.glob('*.log*')
            log = [f.read_text() for f in logFiles]
            log.reverse()
            return ''.join(log)
        
        @self.m_app.get("/api/backup")
        def getBackup():
            return self.m_docker.getBackupList()
        
        @self.m_app.get("/api/history")
        def getRemoteBackups():
            backupList = dict()
            
            remotes = self.m_remote.getRemotes()

            for remote in remotes:
                backupList[remote.getDescriptor()] = remote.getBackupInfo()
            
            return backupList        
        
        self.m_app.mount("/", StaticFiles(directory=self.m_staticDir, html=True), name="static")
