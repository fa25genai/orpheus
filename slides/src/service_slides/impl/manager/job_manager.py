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

    async def init_job(self, lectureId, required_page_count: int) -> None:
        await self.cleanup()
        async with self.mutex:
            self.jobs.add(lectureId)
            self.job_required_counts[lectureId] = required_page_count
            self.job_achieved_counts[lectureId] = 0
            self.job_update_timestamps[lectureId] = datetime.datetime.now()

    async def finish_page(self, lectureId) -> None:
        await self.cleanup()
        async with self.mutex:
            self.job_achieved_counts[lectureId] += 1
            self.job_update_timestamps[lectureId] = datetime.datetime.now()

    async def get_status(self, lectureId) -> JobStatus | None:
        await self.cleanup()
        async with self.mutex:
            if lectureId in self.job_achieved_counts:
                achieved = self.job_achieved_counts[lectureId]
                total = self.job_required_counts[lectureId]
                updated_at = self.job_update_timestamps[lectureId]
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
