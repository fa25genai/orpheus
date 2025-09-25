import datetime
from asyncio import Lock
from threading import Condition
from typing import Dict, Set


class JobStatus:
    total: int
    achieved: int
    error: bool
    uploaded: bool
    updated_at: datetime.datetime
    web_url: str | None
    pdf_url: str | None

    def __init__(self, total: int, achieved: int, error: bool, uploaded: bool, updated_at: datetime.datetime, web_url: str | None, pdf_url: str | None) -> None:
        self.total = total
        self.achieved = achieved
        self.error = error
        self.uploaded = uploaded
        self.updated_at = updated_at
        self.web_url = web_url
        self.pdf_url = pdf_url


class JobManager:
    def __init__(self) -> None:
        self.mutex = Lock()
        self.condition_variable = Condition()
        self.jobs: Set[str] = set()
        self.job_required_counts: Dict[str, int] = dict()
        self.job_achieved_counts: Dict[str, int] = dict()
        self.job_uploaded: Dict[str, bool] = dict()
        self.job_error: Dict[str, bool] = dict()
        self.job_web_urls: Dict[str, str | None] = dict()
        self.job_pdf_urls: Dict[str, str | None] = dict()
        self.job_update_timestamps: Dict[str, datetime.datetime] = dict()

    async def init_job(self, promptId: str, required_page_count: int) -> None:
        await self.cleanup()
        async with self.mutex:
            self.jobs.add(promptId)
            self.job_required_counts[promptId] = required_page_count
            self.job_achieved_counts[promptId] = 0
            self.job_uploaded[promptId] = False
            self.job_error[promptId] = False
            self.job_update_timestamps[promptId] = datetime.datetime.now()

    async def fail(self, promptId: str) -> None:
        await self.cleanup()
        async with self.mutex:
            self.job_error[promptId] = True
            self.job_update_timestamps[promptId] = datetime.datetime.now()

    async def finish_page(self, promptId: str) -> None:
        await self.cleanup()
        async with self.mutex:
            self.job_achieved_counts[promptId] += 1
            self.job_update_timestamps[promptId] = datetime.datetime.now()

    async def finish_upload(self, promptId: str, webUrl: str | None, pdfUrl: str | None) -> None:
        await self.cleanup()
        async with self.mutex:
            self.job_uploaded[promptId] = True
            self.job_web_urls[promptId] = webUrl
            self.job_pdf_urls[promptId] = pdfUrl
            self.job_update_timestamps[promptId] = datetime.datetime.now()
            self.condition_variable.notify_all()

    async def get_status(self, promptId: str) -> JobStatus | None:
        await self.cleanup()
        async with self.mutex:
            if promptId in self.job_achieved_counts:
                achieved = self.job_achieved_counts[promptId]
                total = self.job_required_counts[promptId]
                error = self.job_error[promptId]
                uploaded = self.job_uploaded[promptId]
                updated_at = self.job_update_timestamps[promptId]
                web_url = self.job_web_urls[promptId] if promptId in self.job_web_urls else None
                pdf_url = self.job_pdf_urls[promptId] if promptId in self.job_pdf_urls else None
                return JobStatus(total, achieved, error, uploaded, updated_at, web_url, pdf_url)
            return None

    async def cleanup(self) -> None:
        to_remove = set()
        async with self.mutex:
            # Remove jobs with update timestamps older than 4 hours
            for job in self.jobs:
                last_update = self.job_update_timestamps[job]
                if (
                    last_update + datetime.timedelta(seconds=4 * 60 * 60)
                ) < datetime.datetime.now():
                    to_remove.add(job)
            for job in to_remove:
                    self.jobs.remove(job)
                    del self.job_required_counts[job]
                    del self.job_achieved_counts[job]
                    del self.job_update_timestamps[job]
