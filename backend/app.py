import falcon
from waitress import serve

from api.containers import ContainersResource
from api.resources import HostResourcesResource, StoragePoolsResource


app = falcon.App()

containers_resource = ContainersResource()
host_resources_resource = HostResourcesResource()
storage_pools_resource = StoragePoolsResource()

app.add_route("/api/containers", containers_resource)
app.add_route("/api/host/resources", host_resources_resource)
app.add_route("/api/storage-pools", storage_pools_resource)


class HealthResource:
    def on_get(self, req, resp):
        resp.media = {
            "status": "ok"
        }
        resp.status = falcon.HTTP_200


app.add_route("/api/health", HealthResource())


if __name__ == "__main__":
    serve(
        app,
        host="127.0.0.1",
        port=8000,
        threads=4,
    )