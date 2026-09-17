from datetime import datetime, timezone

import pylxd


class LXDService:
    ALLOWED_UBUNTU_RELEASES = {
        "24.04",
        "22.04",
    }

    def __init__(self):
        self.client = pylxd.Client()

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

    def _serialize_container(self, container):
        config = container.expanded_config or {}

        data = {
            "name": container.name,
            "lxd_uuid": config.get("volatile.uuid"),
            "status": container.status,
            "type": "container",
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "image": {
                "os": config.get("image.os"),
                "version": config.get("image.version"),
                "release": config.get("image.release"),
                "architecture": config.get("image.architecture"),
                "description": config.get("image.description"),
            },
            "limits": {
                "cpu": config.get("limits.cpu"),
                "memory": config.get("limits.memory"),
            },
            "ipv4": None,
            "pid": None,
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
                "total_bytes": None,
            },
            "network": {
                "rx_bytes": 0,
                "tx_bytes": 0,
            },
        }

        # A stopped container does not have meaningful live metrics.
        if container.status != "Running":
            return data

        state = container.state()

        data["pid"] = state.pid
        data["processes"] = state.processes or 0

        # CPU
        cpu = state.cpu or {}
        data["cpu"]["usage_ns"] = cpu.get("usage", 0)

        # Memory
        memory = state.memory or {}

        used_memory = memory.get("usage", 0) or 0
        total_memory = memory.get("total", 0) or 0

        data["memory"]["used_bytes"] = used_memory
        data["memory"]["reported_total_bytes"] = total_memory

        if total_memory > 0:
            data["memory"]["percent"] = round(
                (used_memory / total_memory) * 100,
                2,
            )

        # Disk
        disk = state.disk or {}
        root_disk = disk.get("root", {})

        disk_usage = root_disk.get("usage")
        disk_total = root_disk.get("total")

        if disk_total and disk_total > 0:
            data["disk"]["used_bytes"] = disk_usage
            data["disk"]["total_bytes"] = disk_total

        # Network
        network = state.network or {}

        rx_bytes = 0
        tx_bytes = 0

        for interface_name, interface in network.items():
            # Ignore loopback traffic.
            if interface_name == "lo":
                continue

            counters = interface.get("counters", {})

            rx_bytes += counters.get("bytes_received", 0)
            tx_bytes += counters.get("bytes_sent", 0)

            # Pick the first global IPv4 address.
            if data["ipv4"] is None:
                for address in interface.get("addresses", []):
                    if (
                        address.get("family") == "inet"
                        and address.get("scope") == "global"
                    ):
                        data["ipv4"] = address.get("address")
                        break

        data["network"]["rx_bytes"] = rx_bytes
        data["network"]["tx_bytes"] = tx_bytes

        return data