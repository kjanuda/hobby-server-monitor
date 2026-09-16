import falcon

from services.lxd_service import LXDService


class ContainersResource:
    def __init__(self):
        self.lxd_service = LXDService()

    def on_get(self, req, resp):
        try:
            containers = self.lxd_service.list_containers()

            resp.media = {
                "containers": containers,
                "count": len(containers),
            }

            resp.status = falcon.HTTP_200

        except Exception:
            resp.media = {
                "error": "LXD service is currently unavailable."
            }

            resp.status = falcon.HTTP_503