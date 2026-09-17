import re

from repositories.container_repository import (
    ContainerRepository,
)
from services.audit_service import AuditService
from services.lxd_service import LXDService
from services.quota_service import (
    QuotaService,
    QuotaValidationError,
)
from services.resource_utils import (
    parse_size_to_bytes,
)


class ContainerCreationError(Exception):
    pass


class ContainerCreationService:
    ALLOWED_IMAGES = {
        "24.04",
        "22.04",
    }

    def __init__(self):
        self.lxd_service = LXDService()
        self.quota_service = QuotaService()
        self.container_repository = (
            ContainerRepository()
        )
        self.audit_service = AuditService()

    def create(
        self,
        name,
        image_alias,
        memory,
        cpu_cores,
        cpu_allowance,
        disk,
        storage_pool,
        network,
        owner_user_id=None,
        ephemeral=False,
        autostart=True,
        description=None,
        actor_email=None,
    ):
        name = self._validate_name(name)

        if image_alias not in self.ALLOWED_IMAGES:
            raise ContainerCreationError(
                "Unsupported image alias."
            )

        try:
            memory_bytes = parse_size_to_bytes(
                memory
            )

            disk_bytes = parse_size_to_bytes(
                disk
            )

        except ValueError as exc:
            raise ContainerCreationError(
                str(exc)
            ) from exc

        if (
            not isinstance(cpu_cores, int)
            or isinstance(cpu_cores, bool)
        ):
            raise ContainerCreationError(
                "CPU cores must be an integer."
            )

        if (
            not isinstance(cpu_allowance, int)
            or isinstance(cpu_allowance, bool)
            or cpu_allowance < 1
            or cpu_allowance > 100
        ):
            raise ContainerCreationError(
                "CPU allowance must be between "
                "1 and 100 percent."
            )

        self._validate_network(network)

        if self._container_name_exists(name):
            raise ContainerCreationError(
                "A container with this name "
                "already exists."
            )

        try:
            self.quota_service.validate_creation(
                owner_user_id=owner_user_id,
                memory_bytes=memory_bytes,
                cpu_cores=cpu_cores,
                disk_bytes=disk_bytes,
                storage_pool=storage_pool,
            )

        except QuotaValidationError as exc:
            raise ContainerCreationError(
                str(exc)
            ) from exc

        container = None

        try:
            container = (
                self.lxd_service.create_container(
                    name=name,
                    image_alias=image_alias,
                    memory_bytes=memory_bytes,
                    cpu_cores=cpu_cores,
                    cpu_allowance=cpu_allowance,
                    disk_bytes=disk_bytes,
                    storage_pool=storage_pool,
                    network=network,
                    ephemeral=ephemeral,
                    autostart=autostart,
                    description=description,
                )
            )

            config = (
                container.expanded_config or {}
            )

            lxd_uuid = config.get(
                "volatile.uuid"
            )

            if not lxd_uuid:
                raise ContainerCreationError(
                    "LXD did not return a stable "
                    "container UUID."
                )

            record = (
                self.container_repository
                .upsert_container(
                    lxd_uuid=lxd_uuid,
                    lxd_name=container.name,
                    description=description,
                )
            )

            if owner_user_id is not None:
                record = (
                    self.container_repository
                    .set_owner(
                        record["id"],
                        owner_user_id,
                    )
                )

            self.audit_service.log(
                action="container.created",
                actor_email=actor_email,
                user_id=owner_user_id,
                container_id=record["id"],
                details={
                    "name": name,
                    "image": image_alias,
                    "memory_bytes": memory_bytes,
                    "cpu_cores": cpu_cores,
                    "cpu_allowance": (
                        cpu_allowance
                    ),
                    "disk_bytes": disk_bytes,
                    "storage_pool": storage_pool,
                    "network": network,
                    "ephemeral": bool(ephemeral),
                    "autostart": bool(autostart),
                },
            )

            return record

        except ContainerCreationError:
            if container is not None:
                self._rollback_container(
                    container.name
                )

            raise

        except Exception as exc:
            if container is not None:
                self._rollback_container(
                    container.name
                )

            raise ContainerCreationError(
                "LXD container creation failed."
            ) from exc

    def _validate_network(self, network):
        networks = (
            self.lxd_service.get_networks()
        )

        valid_networks = {
            item["name"]
            for item in networks
            if item["managed"]
        }

        if network not in valid_networks:
            raise ContainerCreationError(
                "Selected network does not exist "
                "or is not managed by LXD."
            )

    def _container_name_exists(self, name):
        return any(
            container.name == name
            for container
            in self.lxd_service.client.containers.all()
        )

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str):
            raise ContainerCreationError(
                "Container name must be a string."
            )

        name = name.strip().lower()

        if (
            len(name) < 1
            or len(name) > 63
        ):
            raise ContainerCreationError(
                "Container name must be between "
                "1 and 63 characters."
            )

        if not re.fullmatch(
            r"[a-z][a-z0-9-]*",
            name,
        ):
            raise ContainerCreationError(
                "Container name must start with "
                "a letter and contain only "
                "lowercase letters, digits, "
                "and hyphens."
            )

        if name.endswith("-"):
            raise ContainerCreationError(
                "Container name cannot end "
                "with a hyphen."
            )

        return name

    def _rollback_container(self, name):
        try:
            self.lxd_service.delete_container_by_name(
                name
            )
        except Exception:
            pass