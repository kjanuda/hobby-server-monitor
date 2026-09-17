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