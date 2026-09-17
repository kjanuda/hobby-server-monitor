import os
from datetime import datetime, timezone
from pathlib import Path

import pylxd

from services.resource_utils import parse_size_to_bytes


class LXDService:
    ALLOWED_UBUNTU_RELEASES = {
        "24.04",
        "22.04",
    }

    DISK_USAGE_CACHE_SECONDS = 60

    def __init__(self):
        self.client = pylxd.Client()
        self._disk_usage_cache = {}

    def list_containers(self):
        """Return all LXD containers with their current runtime state."""
        return [
            self._serialize_container(container)
            for container in self.client.containers.all()
        ]

    def get_container(self, name):
        """Return a single container with its current runtime state."""
        container = self.client.containers.get(name)

        return self._serialize_container(container)

    def list_container_identities(self):
        """Return stable LXD identities for all containers."""
        identities = []

        for container in self.client.containers.all():
            config = container.expanded_config or {}

            lxd_uuid = config.get("volatile.uuid")

            if not lxd_uuid:
                raise RuntimeError(
                    f"Container '{container.name}' "
                    "does not expose volatile.uuid."
                )

            description = getattr(
                container,
                "description",
                None,
            )

            identities.append(
                {
                    "lxd_uuid": lxd_uuid,
                    "lxd_name": container.name,
                    "description": description,
                }
            )

        return identities

    def get_host_resources(self):
        """Return host-level CPU and memory resources."""
        response = self.client.api.resources.get()
        resources = response.json()["metadata"]

        cpu = resources.get("cpu", {})
        memory = resources.get("memory", {})

        total_memory = memory.get("total", 0) or 0
        used_memory = memory.get("used", 0) or 0

        return {
            "cpu": {
                "logical_cpus": cpu.get("total", 0),
                "architecture": cpu.get("architecture"),
            },
            "memory": {
                "total_bytes": total_memory,
                "used_bytes": used_memory,
                "available_bytes": max(
                    total_memory - used_memory,
                    0,
                ),
            },
        }

    def get_storage_pools(self):
        """Return storage pool capacity and inode usage."""
        pools = []

        for pool in self.client.storage_pools.all():
            resources = pool.resources.get()

            space = resources.space or {}
            inodes = resources.inodes or {}

            total_space = space.get("total", 0) or 0
            used_space = space.get("used", 0) or 0

            pools.append(
                {
                    "name": pool.name,
                    "driver": pool.driver,
                    "space": {
                        "total_bytes": total_space,
                        "used_bytes": used_space,
                        "available_bytes": max(
                            total_space - used_space,
                            0,
                        ),
                    },
                    "inodes": {
                        "total": inodes.get("total", 0),
                        "used": inodes.get("used", 0),
                    },
                }
            )

        return pools

    def get_networks(self):
        """Return available LXD networks."""
        networks = []

        for network in self.client.networks.all():
            networks.append(
                {
                    "name": network.name,
                    "type": network.type,
                    "managed": network.managed,
                }
            )

        return networks

    def get_image_aliases(self):
        """Return unique aliases from locally available LXD images."""
        aliases = []

        for image in self.client.images.all():
            for alias in image.aliases or []:
                name = alias.get("name")

                if name:
                    aliases.append(name)

        return sorted(set(aliases))

    def create_container(
        self,
        name,
        image_alias,
        memory_bytes,
        cpu_cores,
        cpu_allowance,
        disk_bytes,
        storage_pool,
        network,
        ephemeral=False,
        autostart=True,
        description=None,
    ):
        """Create an Ubuntu LXD container from a remote image."""
        if image_alias not in self.ALLOWED_UBUNTU_RELEASES:
            raise ValueError(
                f"Unsupported Ubuntu release: {image_alias}. "
                f"Allowed releases: "
                f"{', '.join(sorted(self.ALLOWED_UBUNTU_RELEASES))}"
            )

        config = {
            "name": name,
            "description": description or "",
            "ephemeral": bool(ephemeral),
            "profiles": [],
            "config": {
                "limits.memory": f"{memory_bytes}B",
                "limits.cpu": str(cpu_cores),
                "limits.cpu.allowance": (
                    f"{cpu_allowance}%"
                ),
                "boot.autostart": (
                    "true" if autostart else "false"
                ),
            },
            "devices": {
                "root": {
                    "type": "disk",
                    "path": "/",
                    "pool": storage_pool,
                    "size": f"{disk_bytes}B",
                },
                "eth0": {
                    "type": "nic",
                    "name": "eth0",
                    "network": network,
                },
            },
            "source": {
                "type": "image",
                "mode": "pull",
                "server": (
                    "https://cloud-images.ubuntu.com/releases/"
                ),
                "protocol": "simplestreams",
                "alias": image_alias,
            },
        }

        container = self.client.containers.create(
            config,
            wait=True,
        )

        return container

    def delete_container_by_name(self, name):
        """Stop and delete an LXD container by name."""
        container = self.client.containers.get(name)

        if container.status == "Running":
            container.stop(wait=True)

        container.delete(wait=True)

    def _get_process_uptime_seconds(self, pid):
        if not pid:
            return None

        try:
            host_uptime = float(
                Path("/proc/uptime")
                .read_text(encoding="utf-8")
                .split()[0]
            )

            stat = Path(
                f"/proc/{pid}/stat"
            ).read_text(
                encoding="utf-8"
            )

            # Field 2 can contain spaces, so split only
            # after the closing process-name parenthesis.
            fields_after_name = stat.rsplit(
                ") ",
                1,
            )[1].split()

            # /proc/<pid>/stat field 22 = starttime.
            # fields_after_name[0] corresponds to field 3.
            start_ticks = int(
                fields_after_name[19]
            )

            clock_ticks = os.sysconf(
                "SC_CLK_TCK"
            )

            started_at_uptime = (
                start_ticks / clock_ticks
            )

            return round(
                max(
                    host_uptime
                    - started_at_uptime,
                    0,
                ),
                2,
            )

        except (
            OSError,
            ValueError,
            IndexError,
        ):
            return None

    def get_container_disk_usage_bytes(
        self,
        name,
    ):
        container = (
            self.client.containers.get(
                name
            )
        )

        if container.status != "Running":
            return None

        try:
            result = container.execute(
                [
                    "du",
                    "-sx",
                    "--block-size=1",
                    "/",
                ]
            )

            if result.exit_code != 0:
                return None

            first_value = (
                result.stdout
                .strip()
                .split()[0]
            )

            return int(first_value)

        except (
            Exception,
            ValueError,
            IndexError,
        ):
            return None

    def _serialize_container(self, container):
        config = container.expanded_config or {}

        devices = (
            container.expanded_devices or {}
        )

        root_device = devices.get(
            "root",
            {},
        )

        configured_disk_size = (
            root_device.get("size")
        )

        data = {
            "name": container.name,
            "lxd_uuid": config.get("volatile.uuid"),
            "status": container.status,
            "type": "container",
            "sampled_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "image": {
                "os": config.get("image.os"),
                "version": config.get("image.version"),
                "release": config.get("image.release"),
                "architecture": config.get(
                    "image.architecture"
                ),
                "description": config.get(
                    "image.description"
                ),
            },
            "limits": {
                "cpu": config.get("limits.cpu"),
                "memory": config.get("limits.memory"),
            },
            "ipv4": None,
            "pid": None,
            "uptime_seconds": None,
            "processes": 0,
            "cpu": {
                "usage_ns": 0,
            },
            "memory": {
                "used_bytes": 0,
                "reported_total_bytes": 0,
                "percent": None,
            },
            "disk": {
                "used_bytes": None,
                "allocated_bytes": None,
                "percent": None,
                "usage_source": None,
            },
            "network": {
                "rx_bytes": 0,
                "tx_bytes": 0,
            },
        }

        if configured_disk_size:
            try:
                data["disk"][
                    "allocated_bytes"
                ] = parse_size_to_bytes(
                    configured_disk_size
                )

            except ValueError:
                pass

        # A stopped container does not have meaningful live metrics.
        if container.status != "Running":
            return data

        state = container.state()

        data["pid"] = state.pid
        data["uptime_seconds"] = (
            self._get_process_uptime_seconds(
                state.pid
            )
        )
        data["processes"] = state.processes or 0

        # CPU
        cpu = state.cpu or {}
        data["cpu"]["usage_ns"] = cpu.get(
            "usage",
            0,
        )

        # Memory
        memory = state.memory or {}

        used_memory = memory.get(
            "usage",
            0,
        ) or 0

        total_memory = memory.get(
            "total",
            0,
        ) or 0

        data["memory"]["used_bytes"] = (
            used_memory
        )

        data["memory"][
            "reported_total_bytes"
        ] = total_memory

        if total_memory > 0:
            data["memory"]["percent"] = round(
                (used_memory / total_memory) * 100,
                2,
            )

        # Disk
        disk = state.disk or {}

        root_disk = disk.get(
            "root",
            {},
        )

        disk_used = root_disk.get(
            "usage"
        )

        disk_total = root_disk.get(
            "total"
        )

        # Only trust LXD state usage if it reports
        # a meaningful total. In our dir-pool setup
        # 0/0 means usage is unavailable.
        if disk_total and disk_total > 0:
            data["disk"]["used_bytes"] = (
                disk_used or 0
            )

            data["disk"][
                "allocated_bytes"
            ] = disk_total

            data["disk"][
                "usage_source"
            ] = "lxd"

        else:
            # LXD does not provide meaningful disk
            # usage for this storage setup. Use a
            # low-frequency container-side fallback.
            now = datetime.now(
                timezone.utc
            ).timestamp()

            cached = self._disk_usage_cache.get(
                container.name
            )

            if (
                cached is None
                or now - cached["sampled_at"]
                >= self.DISK_USAGE_CACHE_SECONDS
            ):
                disk_used = (
                    self.get_container_disk_usage_bytes(
                        container.name
                    )
                )

                self._disk_usage_cache[
                    container.name
                ] = {
                    "used_bytes": disk_used,
                    "sampled_at": now,
                }

            else:
                disk_used = cached[
                    "used_bytes"
                ]

            if disk_used is not None:
                data["disk"][
                    "used_bytes"
                ] = disk_used

                data["disk"][
                    "usage_source"
                ] = "exec"

        used = data["disk"][
            "used_bytes"
        ]

        allocated = data["disk"][
            "allocated_bytes"
        ]

        if (
            used is not None
            and allocated
            and allocated > 0
        ):
            data["disk"]["percent"] = round(
                (used / allocated) * 100,
                2,
            )

        # Network
        network = state.network or {}

        rx_bytes = 0
        tx_bytes = 0

        for interface_name, interface in network.items():
            # Ignore loopback traffic.
            if interface_name == "lo":
                continue

            counters = interface.get(
                "counters",
                {},
            )

            rx_bytes += counters.get(
                "bytes_received",
                0,
            )

            tx_bytes += counters.get(
                "bytes_sent",
                0,
            )

            # Pick the first global IPv4 address.
            if data["ipv4"] is None:
                for address in interface.get(
                    "addresses",
                    [],
                ):
                    if (
                        address.get("family") == "inet"
                        and address.get("scope") == "global"
                    ):
                        data["ipv4"] = address.get(
                            "address"
                        )
                        break

        data["network"]["rx_bytes"] = rx_bytes
        data["network"]["tx_bytes"] = tx_bytes

        return data