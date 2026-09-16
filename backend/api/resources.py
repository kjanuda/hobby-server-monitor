import falcon

from services.lxd_service import LXDService


class HostResourcesResource:
    def __init__(self):
        self.lxd_service = LXDService()

    def on_get(self, req, resp):
        try:
            resp.media = self.lxd_service.get_host_resources()
            resp.status = falcon.HTTP_200

        except Exception:
            resp.media = {
                "error": "Unable to read host resources."
            }
            resp.status = falcon.HTTP_503


class StoragePoolsResource:
    def __init__(self):
        self.lxd_service = LXDService()

    def on_get(self, req, resp):
        try:
            pools = self.lxd_service.get_storage_pools()

            resp.media = {
                "storage_pools": pools,
                "count": len(pools),
            }
            resp.status = falcon.HTTP_200

        except Exception:
            resp.media = {
                "error": "Unable to read storage pool resources."
            }
            resp.status = falcon.HTTP_503