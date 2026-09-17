import argparse
import time

from config import METRICS_INTERVAL_SECONDS
from services.metrics_collector import (
    MetricsCollector,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--once",
        action="store_true",
        help="Collect one sample and exit.",
    )

    args = parser.parse_args()

    collector = MetricsCollector()

    if args.once:
        inserted = collector.collect_once()

        print(
            f"[collector] inserted "
            f"{inserted} point(s)"
        )

        return

    print(
        "[collector] started "
        f"interval={METRICS_INTERVAL_SECONDS}s",
        flush=True,
    )

    while True:
        started = time.monotonic()

        try:
            inserted = (
                collector.collect_once()
            )

            print(
                f"[collector] inserted "
                f"{inserted} point(s)",
                flush=True,
            )

        except Exception as exc:
            # Collector process must survive
            # temporary failures.
            print(
                f"[collector] cycle failed: "
                f"{exc}",
                flush=True,
            )

        elapsed = (
            time.monotonic() - started
        )

        sleep_seconds = max(
            METRICS_INTERVAL_SECONDS
            - elapsed,
            0,
        )

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()