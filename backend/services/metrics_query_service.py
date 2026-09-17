from datetime import datetime, timedelta, timezone

from repositories.container_repository import (
    ContainerRepository,
)
from services.metrics_store import MetricsStore


class MetricsQueryError(Exception):
    pass


class MetricsQueryService:
    MAX_HOURS = 48
    DEFAULT_MAX_POINTS = 360
    HARD_MAX_POINTS = 720

    def __init__(self):
        self.store = MetricsStore()
        self.container_repository = (
            ContainerRepository()
        )

    def get_history(
        self,
        container_id,
        hours=24,
        max_points=DEFAULT_MAX_POINTS,
    ):
        if (
            not isinstance(hours, int)
            or isinstance(hours, bool)
            or hours < 1
            or hours > self.MAX_HOURS
        ):
            raise MetricsQueryError(
                "hours must be between 1 and 48."
            )

        if (
            not isinstance(max_points, int)
            or isinstance(max_points, bool)
            or max_points < 10
            or max_points > self.HARD_MAX_POINTS
        ):
            raise MetricsQueryError(
                "max_points must be between 10 and 720."
            )

        container = (
            self.container_repository.get_by_id(
                container_id
            )
        )

        if not container:
            raise MetricsQueryError(
                "Container not found."
            )

        since = (
            datetime.now(timezone.utc)
            - timedelta(hours=hours)
        )

        points = self.store.search_container(
            container_uuid=container["lxd_uuid"],
            since=since,
        )

        original_count = len(points)

        points = self._downsample(
            points,
            max_points,
        )

        return {
            "container_id": container["id"],
            "container_name": container[
                "lxd_name"
            ],
            "hours": hours,
            "sample_count": original_count,
            "returned_count": len(points),
            "points": [
                self._serialize_point(point)
                for point in points
            ],
        }

    @staticmethod
    def _serialize_point(point):
        return {
            "time": point.time.isoformat(),
            "state": point.tags.get("state"),
            "cpu_percent": (
                point.fields.get("cpu_percent")
            ),
            "uptime_seconds": (
                point.fields.get(
                    "uptime_seconds"
                )
            ),
            "memory_used_bytes": (
                point.fields.get(
                    "memory_used_bytes"
                )
            ),
            "memory_limit_bytes": (
                point.fields.get(
                    "memory_limit_bytes"
                )
            ),
            "memory_percent": (
                point.fields.get(
                    "memory_percent"
                )
            ),
            "processes": (
                point.fields.get("processes")
            ),
            "rx_bytes": (
                point.fields.get("rx_bytes")
            ),
            "tx_bytes": (
                point.fields.get("tx_bytes")
            ),
            "rx_bytes_per_second": (
                point.fields.get(
                    "rx_bytes_per_second"
                )
            ),
            "tx_bytes_per_second": (
                point.fields.get(
                    "tx_bytes_per_second"
                )
            ),
            "disk_used_bytes": (
                point.fields.get(
                    "disk_used_bytes"
                )
            ),
            "disk_allocated_bytes": (
                point.fields.get(
                    "disk_allocated_bytes"
                )
            ),
            "disk_percent": (
                point.fields.get(
                    "disk_percent"
                )
            ),
        }

    @staticmethod
    def _downsample(points, max_points):
        count = len(points)

        if count <= max_points:
            return points

        if max_points == 1:
            return [points[-1]]

        indexes = {
            round(
                index
                * (count - 1)
                / (max_points - 1)
            )
            for index in range(max_points)
        }

        return [
            points[index]
            for index in sorted(indexes)
        ]