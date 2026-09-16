import pylxd
from pylxd.exceptions import LXDAPIException


class LXDService:
    def __init__(self):
        self.client = pylxd.Client()

    def list_containers(self):
        containers = self.client.containers.all()

        return [
            {
                "name": container.name,
                "status": container.status,
                "type": "container",
            }
            for container in containers
        ]