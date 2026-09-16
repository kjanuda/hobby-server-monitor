from datetime import datetime, timezone

import pylxd


class LXDService:
    def __init__(self):
        self.client = pylxd.Client()

    def list_containers(self):
        """Return all LXD containers with their current runtime state."""
        return [
            self._serialize_container(container)
            for container in self.client.containers.all()
        ]

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

    def _serialize_container(self, container):
        config = container.expanded_config or {}

        data = {
            "name": container.name,
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

        data["disk"]["used_bytes"] = root_disk.get("usage")
        data["disk"]["total_bytes"] = root_disk.get("total")

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