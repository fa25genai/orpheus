from __future__ import annotations
from time import sleep
from app.workers.queues import purge_stale_jobs, CLEANUP_INTERVAL_SECONDS

def loop() -> None:
    while True:
        purge_stale_jobs()
        sleep(CLEANUP_INTERVAL_SECONDS)