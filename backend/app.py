import falcon
from waitress import serve

from api.containers import ContainersResource


app = falcon.App()

containers_resource = ContainersResource()

app.add_route("/api/containers", containers_resource)


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