import falcon

from repositories.container_repository import (
    ContainerRepository,
)
from services.lxd_service import LXDService
from services.container_access_service import (
    ContainerAccessForbiddenError,
    ContainerAccessService,
)


class ContainersResource:
    def __init__(self):
        self.lxd_service = LXDService()
        self.access_service = (
            ContainerAccessService()
        )

    def on_get(self, req, resp):
        try:
            containers = self.lxd_service.list_containers()

            user = req.context.user

            if user["role"] != "admin":
                allowed = (
                    self.access_service.list_for_user(
                        user["id"]
                    )
                )

                allowed_names = {
                    item["lxd_name"]
                    for item in allowed
                }

                containers = [
                    container
                    for container in containers
                    if container["name"] in allowed_names
                ]

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


class ContainerResource:
    def __init__(self):
        self.lxd_service = LXDService()
        self.container_repository = (
            ContainerRepository()
        )
        self.access_service = (
            ContainerAccessService()
        )

    def on_get(
        self,
        req,
        resp,
        container_id,
    ):
        user = req.context.user

        try:
            self.access_service.assert_user_access(
                user,
                container_id,
            )

        except ContainerAccessForbiddenError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_403
            return

        container_record = (
            self.container_repository.get_by_id(
                container_id
            )
        )

        if not container_record:
            resp.media = {
                "error": "Container not found."
            }
            resp.status = falcon.HTTP_404
            return

        try:
            container = (
                self.lxd_service.get_container(
                    container_record["lxd_name"]
                )
            )

        except Exception:
            resp.media = {
                "error": (
                    "Container is currently "
                    "unavailable in LXD."
                )
            }
            resp.status = falcon.HTTP_503
            return

        resp.media = {
            "container_id": container_record["id"],
            "container": container,
        }

        resp.status = falcon.HTTP_200