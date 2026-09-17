from datetime import datetime, timedelta, timezone
from pathlib import Path

from tinyflux import Point, TimeQuery, TinyFlux

from config import (
    METRICS_DB_PATH,
    METRICS_RETENTION_HOURS,
)


class MetricsStore:
    def __init__(self):
        project_root = (
            Path(__file__).resolve().parent.parent.parent
        )

        path = Path(METRICS_DB_PATH)

        if not path.is_absolute():
            path = project_root / path

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path = path

    def insert_points(self, points):
        if not points:
            return 0

        with TinyFlux(str(self.path)) as db:
            return db.insert_multiple(
                points,
                compact_key_prefixes=True,
            )

    def remove_expired(self):
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(
                hours=METRICS_RETENTION_HOURS
            )
        )

        with TinyFlux(str(self.path)) as db:
            return db.remove(
                TimeQuery() < cutoff
            )

    def all_points(self):
        with TinyFlux(str(self.path)) as db:
            return db.all()