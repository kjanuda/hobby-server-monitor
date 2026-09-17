from repositories.container_repository import ContainerRepository
from services.audit_service import AuditService
from services.lxd_service import LXDService
from services.resource_utils import parse_size_to_bytes


class ContainerUpdateError(Exception):
    pass


class ContainerUpdateService:
    def __init__(self):
        self.repository = ContainerRepository()
        self.lxd_service = LXDService()
        self.audit_service = AuditService()

    def update_limits(
        self,
        container_id,
        memory=None,
        cpu_cores=None,
        cpu_allowance=None,
        disk=None,
        actor_email=None,
    ):
        record = self.repository.get_by_id(container_id)

        if not record:
            raise ContainerUpdateError(
                "Container not found."
            )

        try:
            container = (
                self.lxd_service.client
                .containers.get(record["lxd_name"])
            )

            before = {
                "memory": container.config.get(
                    "limits.memory"
                ),
                "cpu": container.config.get(
                    "limits.cpu"
                ),
                "cpu_allowance": container.config.get(
                    "limits.cpu.allowance"
                ),
            }

            if memory is not None:
                memory_bytes = parse_size_to_bytes(
                    memory
                )

                if memory_bytes < 256 * 1024 * 1024:
                    raise ContainerUpdateError(
                        "Memory must be at least 256 MiB."
                    )

                container.config[
                    "limits.memory"
                ] = f"{memory_bytes}B"

            if cpu_cores is not None:
                if (
                    not isinstance(cpu_cores, int)
                    or isinstance(cpu_cores, bool)
                    or cpu_cores < 1
                ):
                    raise ContainerUpdateError(
                        "CPU cores must be a positive integer."
                    )

                host = (
                    self.lxd_service
                    .get_host_resources()
                )

                if (
                    cpu_cores
                    > host["cpu"]["logical_cpus"]
                ):
                    raise ContainerUpdateError(
                        "Requested CPU exceeds host capacity."
                    )

                container.config[
                    "limits.cpu"
                ] = str(cpu_cores)

            if cpu_allowance is not None:
                if (
                    not isinstance(cpu_allowance, int)
                    or isinstance(cpu_allowance, bool)
                    or cpu_allowance < 1
                    or cpu_allowance > 100
                ):
                    raise ContainerUpdateError(
                        "CPU allowance must be between 1 and 100."
                    )

                container.config[
                    "limits.cpu.allowance"
                ] = f"{cpu_allowance}%"

            if disk is not None:
                disk_bytes = parse_size_to_bytes(
                    disk
                )

                root = dict(
                    container.devices.get(
                        "root",
                        {}
                    )
                )

                current_size = root.get("size")

                if current_size:
                    current_bytes = (
                        parse_size_to_bytes(
                            current_size
                        )
                    )

                    if disk_bytes < current_bytes:
                        raise ContainerUpdateError(
                            "Disk size cannot be reduced."
                        )

                root["size"] = f"{disk_bytes}B"
                container.devices["root"] = root

            container.save(wait=True)

        except ContainerUpdateError:
            raise

        except ValueError as exc:
            raise ContainerUpdateError(
                str(exc)
            ) from exc

        except Exception as exc:
            raise ContainerUpdateError(
                "Unable to update container limits."
            ) from exc

        updated = self.lxd_service.get_container(
            record["lxd_name"]
        )

        self.audit_service.log(
            action="container.limits_updated",
            actor_email=actor_email,
            container_id=container_id,
            details={
                "before": before,
                "requested": {
                    "memory": memory,
                    "cpu_cores": cpu_cores,
                    "cpu_allowance": cpu_allowance,
                    "disk": disk,
                },
            },
        )

        return updated