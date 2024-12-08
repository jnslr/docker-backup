import uvicorn
import json
from dacite import from_dict
from fastapi import FastAPI, Response
from threading import Thread
from pathlib import Path

from definitions import BackupHistory, AppSettings, VolumeInfo
from logger import logger
from backup import BackupCreator

app = FastAPI()
index = Path(__file__).parent.joinpath('static/index.html')

@app.get("/")
def read_root():
    return Response(content=index.read_text(), media_type="text/html")

@app.post("/api/reloadSettings")
def reloadSettings():
    BackupCreator.getInstance().reloadSettings()
    return Response(content="Ok")

@app.get("/api/settings")
def getSettings() -> AppSettings:
    return BackupCreator.getInstance().getSettings()

@app.post("/api/settings")
def updateSettings(newSettings:AppSettings) -> None:
    BackupCreator.getInstance().updateSettings(newSettings)

@app.get("/api/history")
def getHistory() -> BackupHistory:
    return BackupCreator.getInstance().getHistory()

@app.get("/api/volumes")
def getVolumes() -> list[VolumeInfo]:
    return BackupCreator.getInstance().getVolumes()


def startServer() -> Thread:
    logger.info("Starting webserver thread")
    serverThread = Thread(daemon=True,target=uvicorn.run, args=[app], kwargs={'host': '', 'port':80})
    serverThread.start()
    logger.info("Webserver started successfully")
    return serverThread
