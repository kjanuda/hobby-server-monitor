import falcon

from repositories.container_repository import (
    ContainerRepository,
)
from services.lxd_service import LXDService
from services.container_access_service import (
    ContainerAccessForbiddenError,
    ContainerAccessService,
)
from services.container_creation_service import (
    ContainerCreationError,
    ContainerCreationService,
)
from services.authorization import require_admin


class ContainersResource:
    def __init__(self):
        self.lxd_service = LXDService()
        self.access_service = (
            ContainerAccessService()
        )
        self.creation_service = (
            ContainerCreationService()
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

    @falcon.before(require_admin)
    def on_post(self, req, resp):
        data = req.media or {}

        required_fields = {
            "name",
            "image",
            "memory",
            "cpu_cores",
            "cpu_allowance",
            "disk",
            "storage_pool",
            "network",
        }

        missing_fields = [
            field
            for field in required_fields
            if field not in data
        ]

        if missing_fields:
            resp.media = {
                "error": (
                    "Missing required fields: "
                    + ", ".join(
                        sorted(missing_fields)
                    )
                )
            }
            resp.status = falcon.HTTP_400
            return

        try:
            record = self.creation_service.create(
                name=data["name"],
                image_alias=data["image"],
                memory=data["memory"],
                cpu_cores=data["cpu_cores"],
                cpu_allowance=data[
                    "cpu_allowance"
                ],
                disk=data["disk"],
                storage_pool=data[
                    "storage_pool"
                ],
                network=data["network"],
                owner_user_id=data.get(
                    "owner_user_id"
                ),
                ephemeral=data.get(
                    "ephemeral",
                    False,
                ),
                autostart=data.get(
                    "autostart",
                    True,
                ),
                description=data.get(
                    "description"
                ),
                actor_email=(
                    req.context.user["email"]
                ),
            )

        except ContainerCreationError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": (
                "Container created successfully."
            ),
            "container": record,
        }

        resp.status = falcon.HTTP_201


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