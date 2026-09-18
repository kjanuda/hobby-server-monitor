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
from services.container_update_service import (
    ContainerUpdateError,
    ContainerUpdateService,
)
from services.container_deletion_service import (
    ContainerDeletionError,
    ContainerDeletionService,
)
from services.authorization import require_admin


class ContainersResource:
    def __init__(self):
        self.lxd_service = LXDService()
        self.container_repository = (
            ContainerRepository()
        )
        self.access_service = (
            ContainerAccessService()
        )
        self.creation_service = (
            ContainerCreationService()
        )

    def on_get(self, req, resp):
        try:
            containers = self.lxd_service.list_containers()

            records = (
                self.container_repository.list_all()
            )

            records_by_name = {
                record["lxd_name"]: record
                for record in records
            }

            for container in containers:
                record = records_by_name.get(
                    container["name"]
                )

                container["container_id"] = (
                    record["id"]
                    if record
                    else None
                )

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
        self.update_service = (
            ContainerUpdateService()
        )
        self.deletion_service = (
            ContainerDeletionService()
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

    @falcon.before(require_admin)
    def on_patch(
        self,
        req,
        resp,
        container_id,
    ):
        data = req.media or {}

        allowed = {
            "memory",
            "cpu_cores",
            "cpu_allowance",
            "disk",
        }

        unknown = set(data) - allowed

        if unknown:
            resp.media = {
                "error": (
                    "Unknown fields: "
                    + ", ".join(
                        sorted(unknown)
                    )
                )
            }
            resp.status = falcon.HTTP_400
            return

        if not data:
            resp.media = {
                "error": (
                    "No resource changes provided."
                )
            }
            resp.status = falcon.HTTP_400
            return

        try:
            container = (
                self.update_service.update_limits(
                    container_id=container_id,
                    memory=data.get(
                        "memory"
                    ),
                    cpu_cores=data.get(
                        "cpu_cores"
                    ),
                    cpu_allowance=data.get(
                        "cpu_allowance"
                    ),
                    disk=data.get(
                        "disk"
                    ),
                    actor_email=(
                        req.context.user[
                            "email"
                        ]
                    ),
                )
            )

        except ContainerUpdateError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": (
                "Container limits updated."
            ),
            "container": container,
        }

        resp.status = falcon.HTTP_200

    @falcon.before(require_admin)
    def on_delete(
        self,
        req,
        resp,
        container_id,
    ):
        data = req.media or {}

        confirm_name = data.get(
            "confirm_name"
        )

        if not confirm_name:
            resp.media = {
                "error": (
                    "confirm_name is required."
                )
            }
            resp.status = falcon.HTTP_400
            return

        try:
            deleted = (
                self.deletion_service.delete(
                    container_id=container_id,
                    confirm_name=confirm_name,
                    actor_email=(
                        req.context.user["email"]
                    ),
                )
            )

        except ContainerDeletionError as exc:
            resp.media = {
                "error": str(exc)
            }
            resp.status = falcon.HTTP_400
            return

        resp.media = {
            "message": (
                "Container deleted successfully."
            ),
            "container": deleted,
        }

        resp.status = falcon.HTTP_200