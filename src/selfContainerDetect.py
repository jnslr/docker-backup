from logger import logger
from docker import DockerClient
from docker.models.containers import Container
import socket

def detectSelfContainer() -> Container:
    client = DockerClient.from_env()
    hostname = socket.gethostname()
    containers = [c for c in client.containers.list() if c.attrs.get('Config',{}).get('Hostname')==hostname]
    if len(containers)<1:
        raise AssertionError(f"Could not detect own container. No conatiner with hostname {hostname}")
    if len(containers)>2:
        raise AssertionError(f"Could not detect own container. Mulitple containers with the same hostname ({hostname}) found")
    selfContainer = containers[0]
    logger.info(f"Detected self container: {selfContainer.name} {selfContainer.id}")
    return selfContainer