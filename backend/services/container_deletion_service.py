from repositories.container_repository import (
    ContainerRepository,
)
from services.audit_service import AuditService
from services.lxd_service import LXDService


class ContainerDeletionError(Exception):
    pass


class ContainerDeletionService:
    def __init__(self):
        self.repository = ContainerRepository()
        self.lxd_service = LXDService()
        self.audit_service = AuditService()

    def delete(
        self,
        container_id,
        confirm_name,
        actor_email=None,
    ):
        record = self.repository.get_by_id(
            container_id
        )

        if not record:
            raise ContainerDeletionError(
                "Container not found."
            )

        if confirm_name != record["lxd_name"]:
            raise ContainerDeletionError(
                "Container name confirmation "
                "does not match."
            )

        snapshot = {
            "container_id": record["id"],
            "name": record["lxd_name"],
            "lxd_uuid": record["lxd_uuid"],
            "owner_user_id": record[
                "owner_user_id"
            ],
        }

        # Record the destructive action request
        # before contacting LXD.
        self.audit_service.log(
            action="container.delete_requested",
            actor_email=actor_email,
            container_id=container_id,
            details=snapshot,
        )

        try:
            self.lxd_service.delete_container_by_name(
                record["lxd_name"]
            )

        except Exception as exc:
            raise ContainerDeletionError(
                "Unable to delete container from LXD."
            ) from exc

        # Remove DB registry row only after LXD
        # deletion succeeds.
        self.repository.delete_by_id(
            container_id
        )

        # container_id is intentionally omitted here,
        # because the registry row no longer exists.
        self.audit_service.log(
            action="container.deleted",
            actor_email=actor_email,
            details=snapshot,
        )

        return snapshot