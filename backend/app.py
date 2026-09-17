import falcon
from waitress import serve

from api.auth import (
    CurrentUserResource,
    GoogleCallbackResource,
    GoogleLoginResource,
    LogoutResource,
)

from api.containers import (
    ContainerResource,
    ContainersResource,
)

from api.metrics import (
    ContainerMetricsResource,
)

from api.resources import (
    HostResourcesResource,
    StoragePoolsResource,
)

from api.users import (
    UserResource,
    UsersResource,
)

from api.container_access import (
    ContainerAccessResource,
)

from api.container_options import (
    ContainerOptionsResource,
)

from api.container_actions import (
    ContainerActionResource,
)

from api.terminal import (
    ContainerTerminalResource,
)

from middleware.authentication import (
    AuthenticationMiddleware,
)


app = falcon.App(
    middleware=[
        AuthenticationMiddleware(),
    ]
)


# ============================================================
# Container and system resources
# ============================================================

containers_resource = ContainersResource()

container_resource = ContainerResource()

container_metrics_resource = (
    ContainerMetricsResource()
)

host_resources_resource = HostResourcesResource()

storage_pools_resource = StoragePoolsResource()

container_options_resource = (
    ContainerOptionsResource()
)

container_action_resource = (
    ContainerActionResource()
)

container_terminal_resource = (
    ContainerTerminalResource()
)


# ============================================================
# Authentication resources
# ============================================================

google_login_resource = GoogleLoginResource()

google_callback_resource = GoogleCallbackResource()

current_user_resource = CurrentUserResource()

logout_resource = LogoutResource()


# ============================================================
# User resources
# ============================================================

users_resource = UsersResource()

user_resource = UserResource()


# ============================================================
# Container access resources
# ============================================================

container_access_resource = (
    ContainerAccessResource()
)


# ============================================================
# Container routes
# ============================================================

app.add_route(
    "/api/containers",
    containers_resource,
)

app.add_route(
    "/api/containers/{container_id:int}",
    container_resource,
)

app.add_route(
    "/api/containers/{container_id:int}/metrics",
    container_metrics_resource,
)

app.add_route(
    "/api/host/resources",
    host_resources_resource,
)

app.add_route(
    "/api/storage-pools",
    storage_pools_resource,
)

app.add_route(
    "/api/container-options",
    container_options_resource,
)

app.add_route(
    "/api/containers/{container_id:int}/actions/{action}",
    container_action_resource,
)

app.add_route(
    "/api/containers/{container_id:int}/terminal",
    container_terminal_resource,
)


# ============================================================
# Authentication routes
# ============================================================

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


# ============================================================
# User routes
# ============================================================

app.add_route(
    "/api/users",
    users_resource,
)

app.add_route(
    "/api/users/{user_id:int}",
    user_resource,
)


# ============================================================
# Container access routes
# ============================================================

app.add_route(
    "/api/users/{user_id:int}/containers/{container_id:int}",
    container_access_resource,
)


# ============================================================
# Health check
# ============================================================

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


# ============================================================
# Application entry point
# ============================================================

if __name__ == "__main__":
    serve(
        app,
        host="127.0.0.1",
        port=8000,
        threads=4,
    )