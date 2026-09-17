import falcon

from services.authorization import require_admin
from services.container_creation_service import (
    ContainerCreationService,
)
from services.lxd_service import LXDService


class ContainerOptionsResource:
    def __init__(self):
        self.lxd_service = LXDService()

    @falcon.before(require_admin)
    def on_get(self, req, resp):
        try:
            networks = [
                network
                for network
                in self.lxd_service.get_networks()
                if network["managed"]
            ]

            pools = (
                self.lxd_service
                .get_storage_pools()
            )

            resp.media = {
                "images": sorted(
                    ContainerCreationService
                    .ALLOWED_IMAGES
                ),
                "networks": networks,
                "storage_pools": pools,
            }

            resp.status = falcon.HTTP_200

        except Exception:
            resp.media = {
                "error": (
                    "Unable to discover "
                    "LXD creation options."
                )
            }

            resp.status = falcon.HTTP_503