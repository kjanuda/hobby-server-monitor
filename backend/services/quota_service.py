from repositories.container_repository import (
    ContainerRepository,
)
from repositories.user_repository import (
    UserRepository,
)
from services.lxd_service import LXDService
from services.resource_utils import (
    parse_size_to_bytes,
)


class QuotaValidationError(Exception):
    pass


class QuotaService:
    MIN_MEMORY_BYTES = 256 * 1024 * 1024
    MIN_DISK_BYTES = 1 * 1024 * 1024 * 1024

    def __init__(self):
        self.user_repository = UserRepository()
        self.container_repository = (
            ContainerRepository()
        )
        self.lxd_service = LXDService()

    def get_user_usage(self, user_id):
        memory_used = 0
        cpu_used = 0
        disk_used = 0

        containers = (
            self.container_repository.list_all()
        )

        for record in containers:
            if record["owner_user_id"] != user_id:
                continue

            try:
                container = (
                    self.lxd_service.client
                    .containers.get(
                        record["lxd_name"]
                    )
                )
            except Exception:
                continue

            config = container.expanded_config or {}
            devices = container.expanded_devices or {}

            memory_limit = config.get(
                "limits.memory"
            )

            if memory_limit:
                try:
                    memory_used += (
                        parse_size_to_bytes(
                            memory_limit
                        )
                    )
                except ValueError:
                    pass

            cpu_limit = config.get(
                "limits.cpu"
            )

            if cpu_limit:
                try:
                    cpu_used += int(cpu_limit)
                except ValueError:
                    pass

            root = devices.get("root", {})
            disk_limit = root.get("size")

            if disk_limit:
                try:
                    disk_used += (
                        parse_size_to_bytes(
                            disk_limit
                        )
                    )
                except ValueError:
                    pass

        return {
            "ram_bytes": memory_used,
            "cpu": cpu_used,
            "disk_bytes": disk_used,
        }

    def validate_creation(
        self,
        owner_user_id,
        memory_bytes,
        cpu_cores,
        disk_bytes,
        storage_pool,
    ):
        if memory_bytes < self.MIN_MEMORY_BYTES:
            raise QuotaValidationError(
                "Memory limit must be at least 256 MiB."
            )

        if disk_bytes < self.MIN_DISK_BYTES:
            raise QuotaValidationError(
                "Disk limit must be at least 1 GiB."
            )

        if cpu_cores < 1:
            raise QuotaValidationError(
                "At least one CPU core is required."
            )

        host = self.lxd_service.get_host_resources()

        host_cpus = host["cpu"]["logical_cpus"]
        host_available_memory = (
            host["memory"]["available_bytes"]
        )

        if cpu_cores > host_cpus:
            raise QuotaValidationError(
                "Requested CPU exceeds host capacity."
            )

        if memory_bytes > host_available_memory:
            raise QuotaValidationError(
                "Requested memory exceeds "
                "currently available host memory."
            )

        pools = (
            self.lxd_service.get_storage_pools()
        )

        pool = next(
            (
                item
                for item in pools
                if item["name"] == storage_pool
            ),
            None,
        )

        if not pool:
            raise QuotaValidationError(
                "Storage pool does not exist."
            )

        if (
            disk_bytes
            > pool["space"]["available_bytes"]
        ):
            raise QuotaValidationError(
                "Requested disk exceeds available "
                "storage pool capacity."
            )

        if owner_user_id is None:
            return

        user = self.user_repository.get_user_by_id(
            owner_user_id
        )

        if not user:
            raise QuotaValidationError(
                "Owner user does not exist."
            )

        if not user["active"]:
            raise QuotaValidationError(
                "Owner user is revoked."
            )

        usage = self.get_user_usage(
            owner_user_id
        )

        requested_ram_total = (
            usage["ram_bytes"]
            + memory_bytes
        )

        requested_cpu_total = (
            usage["cpu"]
            + cpu_cores
        )

        requested_disk_total = (
            usage["disk_bytes"]
            + disk_bytes
        )

        if (
            user["ram_quota_bytes"] > 0
            and requested_ram_total
            > user["ram_quota_bytes"]
        ):
            raise QuotaValidationError(
                "Requested memory exceeds "
                "the user's remaining RAM quota."
            )

        if (
            user["cpu_quota"] > 0
            and requested_cpu_total
            > user["cpu_quota"]
        ):
            raise QuotaValidationError(
                "Requested CPU exceeds "
                "the user's remaining CPU quota."
            )

        if (
            user["disk_quota_bytes"] > 0
            and requested_disk_total
            > user["disk_quota_bytes"]
        ):
            raise QuotaValidationError(
                "Requested disk exceeds "
                "the user's remaining disk quota."
            )

    def validate_update(
        self,
        container_id,
        memory_bytes,
        cpu_cores,
        disk_bytes,
        storage_pool,
    ):
        record = self.container_repository.get_by_id(
            container_id
        )

        if not record:
            raise QuotaValidationError(
                "Container not found."
            )

        try:
            container = (
                self.lxd_service.client
                .containers.get(
                    record["lxd_name"]
                )
            )
        except Exception as exc:
            raise QuotaValidationError(
                "Container is unavailable in LXD."
            ) from exc

        config = container.expanded_config or {}
        devices = container.expanded_devices or {}

        current_memory = 0
        current_cpu = 0
        current_disk = 0

        current_memory_value = config.get(
            "limits.memory"
        )

        if current_memory_value:
            try:
                current_memory = parse_size_to_bytes(
                    current_memory_value
                )
            except ValueError:
                current_memory = 0

        current_cpu_value = config.get(
            "limits.cpu"
        )

        if current_cpu_value:
            try:
                current_cpu = int(
                    current_cpu_value
                )
            except ValueError:
                current_cpu = 0

        root = devices.get("root", {})

        current_disk_value = root.get("size")

        if current_disk_value:
            try:
                current_disk = parse_size_to_bytes(
                    current_disk_value
                )
            except ValueError:
                current_disk = 0

        if memory_bytes < self.MIN_MEMORY_BYTES:
            raise QuotaValidationError(
                "Memory limit must be at least 256 MiB."
            )

        if disk_bytes < self.MIN_DISK_BYTES:
            raise QuotaValidationError(
                "Disk limit must be at least 1 GiB."
            )

        if cpu_cores < 1:
            raise QuotaValidationError(
                "At least one CPU core is required."
            )

        host = self.lxd_service.get_host_resources()

        if cpu_cores > host["cpu"]["logical_cpus"]:
            raise QuotaValidationError(
                "Requested CPU exceeds host capacity."
            )

        memory_increase = max(
            memory_bytes - current_memory,
            0,
        )

        if (
            memory_increase
            > host["memory"]["available_bytes"]
        ):
            raise QuotaValidationError(
                "Requested memory increase exceeds "
                "currently available host memory."
            )

        pools = self.lxd_service.get_storage_pools()

        pool = next(
            (
                item
                for item in pools
                if item["name"] == storage_pool
            ),
            None,
        )

        if not pool:
            raise QuotaValidationError(
                "Storage pool does not exist."
            )

        disk_increase = max(
            disk_bytes - current_disk,
            0,
        )

        if (
            disk_increase
            > pool["space"]["available_bytes"]
        ):
            raise QuotaValidationError(
                "Requested disk increase exceeds "
                "available storage capacity."
            )

        owner_user_id = record["owner_user_id"]

        if owner_user_id is None:
            return

        user = self.user_repository.get_user_by_id(
            owner_user_id
        )

        if not user:
            raise QuotaValidationError(
                "Container owner does not exist."
            )

        if not user["active"]:
            raise QuotaValidationError(
                "Container owner is not active."
            )

        usage = self.get_user_usage(
            owner_user_id
        )

        new_ram_total = (
            usage["ram_bytes"]
            - current_memory
            + memory_bytes
        )

        new_cpu_total = (
            usage["cpu"]
            - current_cpu
            + cpu_cores
        )

        new_disk_total = (
            usage["disk_bytes"]
            - current_disk
            + disk_bytes
        )

        if (
            user["ram_quota_bytes"] > 0
            and new_ram_total
            > user["ram_quota_bytes"]
        ):
            raise QuotaValidationError(
                "Updated memory exceeds "
                "the owner's RAM quota."
            )

        if (
            user["cpu_quota"] > 0
            and new_cpu_total
            > user["cpu_quota"]
        ):
            raise QuotaValidationError(
                "Updated CPU exceeds "
                "the owner's CPU quota."
            )

        if (
            user["disk_quota_bytes"] > 0
            and new_disk_total
            > user["disk_quota_bytes"]
        ):
            raise QuotaValidationError(
                "Updated disk exceeds "
                "the owner's disk quota."
            )

