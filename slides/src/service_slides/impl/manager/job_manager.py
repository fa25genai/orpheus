import datetime
import logging
from asyncio import Lock
from typing import Dict

_log = logging.getLogger("job_manager")


class JobHandle:
    def __init__(self, id: str, total_count: int) -> None:
        self.id = id
        self.total_count = total_count
        self.current_count = 0
        self.updated_at = datetime.datetime.now()

    def increment_count(self) -> int:
        self.current_count += 1
        self.updated_at = datetime.datetime.now()
        return self.current_count


class JobManager:
    def __init__(self) -> None:
        self.mutex = Lock()
        self.jobs: Dict[str, JobHandle] = dict()

    async def init_job(self, promptId: str, required_page_count: int) -> None:
        await self.cleanup()
        async with self.mutex:
            _log.debug("Initializing job %s", promptId)
            self.jobs[promptId] = JobHandle(promptId, required_page_count)

    async def finish_page(self, promptId: str) -> int:
        await self.cleanup()
        async with self.mutex:
            _log.debug("Incrementing finished pages for %s", promptId)
            return self.jobs[promptId].increment_count()

    async def cleanup(self) -> None:
        _log.debug("Cleaning up jobs")
        to_remove = set()
        async with self.mutex:
            # Remove jobs with update timestamps older than 4 hours
            for id, job in self.jobs.items():
                last_update = job.updated_at
                if (last_update + datetime.timedelta(seconds=4 * 60 * 60)) < datetime.datetime.now():
                    to_remove.add(id)
            for id in to_remove:
                _log.debug("Removing job %s (Last modified: %s)", id, self.jobs[id].updated_at)
                del self.jobs[id]
