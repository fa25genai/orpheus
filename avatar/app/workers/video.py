from __future__ import annotations
from app.schemas import ErrorModel, VideoTask, Job
from app.services.media_io import generate_video
from app.services.status import update_avatar_generation_step_status
from app.workers.queues import VIDEO_QUEUE, JOBS, utcnow

def loop() -> None:
    print("[video-worker] started")
    while True:
        task: VideoTask = VIDEO_QUEUE.get()
        pid = task.promptId
        video_done = False
        try:
            vpath = generate_video(
                audio_path=task.audioPath,
                prompt_id=pid,
                course_id=task.courseId,
                user_profile=task.userProfile,
                video_counter=task.slideNo,
                source_image_path=task.sourceImagePath,
            )
            if vpath:
                update_avatar_generation_step_status(pid, task.slideNo, video="DONE")
                video_done = True
            else:
                update_avatar_generation_step_status(pid, task.slideNo, video="FAILED")

        except Exception as e:
            if not video_done:
                update_avatar_generation_step_status(pid, task.slideNo, video="FAILED")
            print(f"[video-worker] error on slide {task.slideNo} for {pid}: {e!r}")
            job = JOBS.get(pid)
            if job:
                t = utcnow()
                job.status = "FAILED"
                job.lastUpdated = t
                job.lastTouched = t
                job.error = ErrorModel(code="GENERATION_FAILED", message=str(e))
                JOBS[pid] = job
        finally:
            VIDEO_QUEUE.task_done()
            job = JOBS.get(pid)
            if job and job.status != "FAILED":
                t = utcnow()
                job.lastUpdated = t
                job.lastTouched = t
                JOBS[pid] = job