from repositories.container_access_repository import (
    ContainerAccessRepository,
)
from repositories.container_repository import (
    ContainerRepository,
)
from repositories.user_repository import UserRepository
from services.audit_service import AuditService


class ContainerAccessError(Exception):
    pass


class ContainerAccessNotFoundError(Exception):
    pass


class ContainerAccessForbiddenError(Exception):
    pass


class ContainerAccessService:
    def __init__(self):
        self.access_repository = (
            ContainerAccessRepository()
        )
        self.container_repository = (
            ContainerRepository()
        )
        self.user_repository = UserRepository()
        self.audit_service = AuditService()

    def assign(
        self,
        user_id,
        container_id,
        actor_email=None,
    ):
        user = self.user_repository.get_user_by_id(
            user_id
        )

        if not user:
            raise ContainerAccessError(
                "User not found."
            )

        if not user["active"]:
            raise ContainerAccessError(
                "Cannot assign a container "
                "to a revoked user."
            )

        container = (
            self.container_repository.get_by_id(
                container_id
            )
        )

        if not container:
            raise ContainerAccessError(
                "Container not found."
            )

        self.access_repository.assign(
            user_id,
            container_id,
        )

        self.audit_service.log(
            action="container.assigned",
            actor_email=actor_email,
            user_id=user_id,
            container_id=container_id,
            details={
                "container": container["lxd_name"],
                "user_email": user["email"],
            },
        )

        return container

    def revoke(
        self,
        user_id,
        container_id,
        actor_email=None,
    ):
        container = (
            self.container_repository.get_by_id(
                container_id
            )
        )

        if not container:
            raise ContainerAccessError(
                "Container not found."
            )

        self.access_repository.revoke(
            user_id,
            container_id,
        )

        self.audit_service.log(
            action="container.unassigned",
            actor_email=actor_email,
            user_id=user_id,
            container_id=container_id,
            details={
                "container": container["lxd_name"],
            },
        )

    def list_for_user(self, user_id):
        return self.access_repository.list_for_user(
            user_id
        )

    def list_assignments_for_user(self, user_id):
        user = self.user_repository.get_user_by_id(
            user_id
        )

        if not user:
            raise ContainerAccessNotFoundError(
                "User not found."
            )

        return self.access_repository.list_for_user(
            user_id
        )

    def user_has_access(
        self,
        user_id,
        container_id,
    ):
        return self.access_repository.has_access(
            user_id,
            container_id,
        )

    def assert_user_access(
        self,
        user,
        container_id,
    ):
        if user["role"] == "admin":
            return

        if not self.user_has_access(
            user["id"],
            container_id,
        ):
            raise ContainerAccessForbiddenError(
                "You do not have access to this container."
            )