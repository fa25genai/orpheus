from __future__ import annotations

from time import sleep

from app.workers.queues import CLEANUP_INTERVAL_SECONDS, purge_stale_jobs


def loop() -> None:
    while True:
        purge_stale_jobs()
        sleep(CLEANUP_INTERVAL_SECONDS)
