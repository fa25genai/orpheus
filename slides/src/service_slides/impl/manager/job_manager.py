import datetime
from asyncio import Lock


class JobStatus:
    total: int
    achieved: int
    updated_at: datetime

    def __init__(self, total: int, achieved: int, updated_at: datetime) -> None:
        self.total = total
        self.achieved = achieved
        self.updated_at = updated_at


class JobManager:
    def __init__(self):
        self.mutex = Lock()
        self.jobs = set()
        self.job_required_counts = dict()
        self.job_achieved_counts = dict()
        self.job_update_timestamps = dict()

    async def init_job(self, promptId, required_page_count: int) -> None:
        await self.cleanup()
        async with self.mutex:
            self.jobs.add(promptId)
            self.job_required_counts[promptId] = required_page_count
            self.job_achieved_counts[promptId] = 0
            self.job_update_timestamps[promptId] = datetime.datetime.now()

    async def finish_page(self, promptId) -> None:
        await self.cleanup()
        async with self.mutex:
            self.job_achieved_counts[promptId] += 1
            self.job_update_timestamps[promptId] = datetime.datetime.now()

    async def get_status(self, promptId) -> JobStatus | None:
        await self.cleanup()
        async with self.mutex:
            if promptId in self.job_achieved_counts:
                achieved = self.job_achieved_counts[promptId]
                total = self.job_required_counts[promptId]
                updated_at = self.job_update_timestamps[promptId]
                return JobStatus(total, achieved, updated_at)
            return None

    async def cleanup(self) -> None:
        async with self.mutex:
            # Remove jobs with update timestamps older than 4 hours
            for job in self.jobs:
                last_update = self.job_update_timestamps[job]
                if (
                    last_update + datetime.timedelta(seconds=4 * 60 * 60)
                ) < datetime.datetime.now():
                    print(job, last_update)
                    self.jobs.remove(job)
                    del self.job_required_counts[job]
                    del self.job_achieved_counts[job]
                    del self.job_update_timestamps[job]
