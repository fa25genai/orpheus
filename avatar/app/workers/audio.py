from __future__ import annotations

from app.db import SessionLocal
from app.schemas import ErrorModel, Job, SlideTask
from app.services.media_io import generate_audio
from app.services.status import update_avatar_generation_step_status
from app.workers.queues import AUDIO_QUEUE, JOBS, VIDEO_QUEUE, estimate_total_seconds_for_new_slide, folder_url, purge_stale_jobs, utcnow
from media import avatar_queries


def loop() -> None:
    print("[audio-worker] started")
    while True:
        task: SlideTask = AUDIO_QUEUE.get()
        pid = task.promptId
        now = utcnow()
        purge_stale_jobs(now)
        job = JOBS.get(pid)

        if not job:
            job = Job(
                promptId=pid,
                status="IN_PROGRESS",
                lastUpdated=now,
                lastTouched=now,
                resultUrl=folder_url(pid),
                startedAt=now,
                expectedDurationSec=0,
                error=None,
            )
            JOBS[pid] = job
        else:
            job.lastTouched = now

        job.status = "IN_PROGRESS"
        job.lastUpdated = now
        job.lastTouched = now
        estimate_total_seconds_for_new_slide(job)
        JOBS[pid] = job

        audio_done = False
        try:
            with SessionLocal() as db:
                update_avatar_generation_step_status(pid, task.slideNo, audio="IN_PROGRESS")

                aurl = generate_audio(
                    voiceTrack=task.text,
                    course_id=task.courseId,
                    prompt_id=pid,
                    user_profile=task.userProfile,
                    audio_counter=task.slideNo,
                    db=db,
                    slot=getattr(task, "slot", "default"),
                )

                if aurl:
                    update_avatar_generation_step_status(pid, task.slideNo, audio="DONE")
                    audio_done = True

                    update_avatar_generation_step_status(pid, task.slideNo, video="IN_PROGRESS")

                    source_path = None
                    try:
                        img = avatar_queries.get_latest_image_for_course_slot(
                            db,
                            course_id=task.courseId,
                            slot=getattr(task, "slot", "default"),
                        )
                        source_path = img.file_path
                    except Exception as e:
                        print(f"[audio-worker] no image for course/slot: {e!r}")

                    from app.schemas import VideoTask
                    VIDEO_QUEUE.put(
                        VideoTask(
                            promptId=pid,
                            courseId=task.courseId,
                            userProfile=task.userProfile,
                            slideNo=task.slideNo,
                            audioPath=aurl,
                            slot=getattr(task, "slot", "default"),
                            sourceImagePath=source_path,
                        )
                    )
                else:
                    update_avatar_generation_step_status(pid, task.slideNo, audio="FAILED")

        except Exception as e:
            if not audio_done:
                update_avatar_generation_step_status(pid, task.slideNo, audio="FAILED")
            print(f"[audio-worker] error on slide {task.slideNo} for {pid}: {e!r}")
            job = JOBS.get(pid)
            if job:
                t = utcnow()
                job.status = "FAILED"
                job.lastUpdated = t
                job.lastTouched = t
                job.error = ErrorModel(code="GENERATION_FAILED", message=str(e))
                JOBS[pid] = job
        finally:
            AUDIO_QUEUE.task_done()
            job = JOBS.get(pid)
            if job and job.status != "FAILED":
                t = utcnow()
                job.lastUpdated = t
                job.lastTouched = t
                JOBS[pid] = job