import logging

LINE_CHARS = 120

logger = logging.getLogger("PythonBackup")
fmt    = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
ch     = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

def printLine():
    logger.info("-"*LINE_CHARS)

def printHeader():
    logger.info("#"*LINE_CHARS)