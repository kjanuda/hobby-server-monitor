import falcon
from waitress import serve

from api.auth import (
    CurrentUserResource,
    GoogleCallbackResource,
    GoogleLoginResource,
    LogoutResource,
)

from api.containers import ContainersResource
from api.resources import (
    HostResourcesResource,
    StoragePoolsResource,
)


app = falcon.App()


# Container and system resources

containers_resource = ContainersResource()
host_resources_resource = HostResourcesResource()
storage_pools_resource = StoragePoolsResource()


# Authentication resources

google_login_resource = GoogleLoginResource()
google_callback_resource = GoogleCallbackResource()
current_user_resource = CurrentUserResource()
logout_resource = LogoutResource()


# Container routes

app.add_route(
    "/api/containers",
    containers_resource,
)

app.add_route(
    "/api/host/resources",
    host_resources_resource,
)

app.add_route(
    "/api/storage-pools",
    storage_pools_resource,
)


# Authentication routes

app.add_route(
    "/api/auth/google/login",
    google_login_resource,
)

app.add_route(
    "/api/auth/google/callback",
    google_callback_resource,
)

app.add_route(
    "/api/auth/me",
    current_user_resource,
)

app.add_route(
    "/api/auth/logout",
    logout_resource,
)


# Health check

class HealthResource:
    def on_get(self, req, resp):
        resp.media = {
            "status": "ok"
        }
        resp.status = falcon.HTTP_200


app.add_route(
    "/api/health",
    HealthResource(),
)


if __name__ == "__main__":
    serve(
        app,
        host="127.0.0.1",
        port=8000,
        threads=4,
    )