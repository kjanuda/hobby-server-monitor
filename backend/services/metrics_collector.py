import time
from datetime import datetime, timezone

from tinyflux import Point

from config import METRICS_INTERVAL_SECONDS
from services.lxd_service import LXDService
from services.metrics_store import MetricsStore
from services.resource_utils import parse_size_to_bytes


class MetricsCollector:
    def __init__(self):
        self.lxd_service = LXDService()
        self.store = MetricsStore()

        self.previous = {}
        self.last_cleanup = 0.0

    def collect_once(self):
        sampled_at = datetime.now(
            timezone.utc
        )

        monotonic_now = time.monotonic()

        try:
            containers = (
                self.lxd_service.list_containers()
            )

        except Exception as exc:
            print(
                f"[collector] LXD unavailable: {exc}",
                flush=True,
            )
            return 0

        points = []

        for container in containers:
            point = self._build_point(
                container,
                sampled_at,
                monotonic_now,
            )

            points.append(point)

        inserted = self.store.insert_points(
            points
        )

        # Retention cleanup at most once per hour.
        if (
            monotonic_now - self.last_cleanup
            >= 3600
        ):
            try:
                removed = (
                    self.store.remove_expired()
                )

                if removed:
                    print(
                        f"[collector] removed "
                        f"{removed} expired points",
                        flush=True,
                    )

            except Exception as exc:
                print(
                    f"[collector] retention "
                    f"cleanup failed: {exc}",
                    flush=True,
                )

            self.last_cleanup = monotonic_now

        return inserted

    def _build_point(
        self,
        container,
        sampled_at,
        monotonic_now,
    ):
        name = container["name"]
        lxd_uuid = (
            container.get("lxd_uuid")
            or name
        )

        cpu_usage_ns = (
            container["cpu"]["usage_ns"]
            or 0
        )

        rx_bytes = (
            container["network"]["rx_bytes"]
            or 0
        )

        tx_bytes = (
            container["network"]["tx_bytes"]
            or 0
        )

        cpu_percent = 0.0
        rx_rate = 0.0
        tx_rate = 0.0

        previous = self.previous.get(
            lxd_uuid
        )

        if previous:
            elapsed_seconds = (
                monotonic_now
                - previous["monotonic"]
            )

            if elapsed_seconds > 0:
                cpu_delta_ns = max(
                    cpu_usage_ns
                    - previous["cpu_usage_ns"],
                    0,
                )

                cpu_limit = (
                    self._effective_cpu_count(
                        container
                    )
                )

                cpu_percent = (
                    cpu_delta_ns
                    / (
                        elapsed_seconds
                        * 1_000_000_000
                        * cpu_limit
                    )
                    * 100
                )

                cpu_percent = round(
                    max(
                        0.0,
                        min(
                            cpu_percent,
                            100.0,
                        ),
                    ),
                    2,
                )

                rx_rate = round(
                    max(
                        rx_bytes
                        - previous["rx_bytes"],
                        0,
                    )
                    / elapsed_seconds,
                    2,
                )

                tx_rate = round(
                    max(
                        tx_bytes
                        - previous["tx_bytes"],
                        0,
                    )
                    / elapsed_seconds,
                    2,
                )

        self.previous[lxd_uuid] = {
            "monotonic": monotonic_now,
            "cpu_usage_ns": cpu_usage_ns,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
        }

        memory_limit_bytes = (
            self._memory_limit_bytes(
                container
            )
        )

        memory_used_bytes = (
            container["memory"]["used_bytes"]
            or 0
        )

        memory_percent = None

        if memory_limit_bytes > 0:
            memory_percent = round(
                (
                    memory_used_bytes
                    / memory_limit_bytes
                )
                * 100,
                2,
            )

        fields = {
            "cpu_percent": cpu_percent,
            "cpu_usage_ns": cpu_usage_ns,
            "memory_used_bytes": (
                memory_used_bytes
            ),
            "memory_limit_bytes": (
                memory_limit_bytes
            ),
            "processes": (
                container["processes"] or 0
            ),
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_bytes_per_second": rx_rate,
            "tx_bytes_per_second": tx_rate,
        }

        if memory_percent is not None:
            fields["memory_percent"] = (
                memory_percent
            )

        disk_used = container["disk"].get(
            "used_bytes"
        )

        disk_total = container["disk"].get(
            "total_bytes"
        )

        if disk_used is not None:
            fields["disk_used_bytes"] = (
                disk_used
            )

        if disk_total is not None:
            fields["disk_total_bytes"] = (
                disk_total
            )

        return Point(
            time=sampled_at,
            measurement="container_metrics",
            tags={
                "container_uuid": str(
                    lxd_uuid
                ),
                "container_name": name,
                "state": container["status"],
            },
            fields=fields,
        )

    def _effective_cpu_count(
        self,
        container,
    ):
        cpu_limit = container[
            "limits"
        ].get("cpu")

        if cpu_limit:
            try:
                value = int(cpu_limit)

                if value > 0:
                    return value

            except ValueError:
                pass

        try:
            host = (
                self.lxd_service
                .get_host_resources()
            )

            return max(
                host["cpu"]["logical_cpus"],
                1,
            )

        except Exception:
            return 1

    @staticmethod
    def _memory_limit_bytes(
        container,
    ):
        value = container[
            "limits"
        ].get("memory")

        if value:
            try:
                return parse_size_to_bytes(
                    value
                )

            except ValueError:
                pass

        # No explicit allocation.
        return (
            container["memory"].get(
                "reported_total_bytes"
            )
            or 0
        )