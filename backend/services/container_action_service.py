from repositories.container_repository import ContainerRepository
from services.audit_service import AuditService
from services.lxd_service import LXDService


class ContainerActionError(Exception):
    pass


class ContainerActionService:
    ALLOWED_ACTIONS = {
        "start",
        "stop",
        "restart",
        "freeze",
        "unfreeze",
    }

    def __init__(self):
        self.repository = ContainerRepository()
        self.lxd_service = LXDService()
        self.audit_service = AuditService()

    def perform(self, container_id, action, actor_email=None):
        if action not in self.ALLOWED_ACTIONS:
            raise ContainerActionError(
                "Unsupported container action."
            )

        record = self.repository.get_by_id(container_id)

        if not record:
            raise ContainerActionError(
                "Container not found."
            )

        try:
            container = self.lxd_service.client.containers.get(
                record["lxd_name"]
            )

            if action == "start":
                container.start(wait=True)

            elif action == "stop":
                container.stop(wait=True)

            elif action == "restart":
                container.restart(wait=True)

            elif action == "freeze":
                container.freeze(wait=True)

            elif action == "unfreeze":
                container.unfreeze(wait=True)

        except Exception as exc:
            raise ContainerActionError(
                f"Unable to {action} container."
            ) from exc

        self.audit_service.log(
            action=f"container.{action}",
            actor_email=actor_email,
            container_id=container_id,
            details={
                "name": record["lxd_name"],
            },
        )

        return self.lxd_service.get_container(
            record["lxd_name"]
        )