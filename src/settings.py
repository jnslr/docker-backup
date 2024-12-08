import json
from dataclasses import asdict
from dacite  import from_dict
from pathlib import Path

from logger import logger
from definitions import AppSettings, BackupHistory

SETTINGS_PATH = Path('/mnt/data/appSettings.json')
HISTORY_PATH  = Path('/mnt/data/backupHistory.json')

def loadSettings() -> AppSettings:
    settings = AppSettings()
    if SETTINGS_PATH.exists():
        settingsDict = json.loads(SETTINGS_PATH.read_text())
        settings = from_dict(data_class=AppSettings,data=settingsDict)
    print(f"Loaded app settings: {settings}")
    return settings

def saveSettings(settings: AppSettings) -> None:
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text( json.dumps(asdict(settings),indent=4) )
    print(f"Saved app settings: {settings}")
    
def loadBackupHistory() -> BackupHistory:
    history = BackupHistory()
    if HISTORY_PATH.exists():
        history = from_dict(HISTORY_PATH.read_text())
    print(f"Loaded backup history with {len(history.backupList)} entries")
    return history
