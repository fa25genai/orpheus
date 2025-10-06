from __future__ import annotations

from app.schemas import ErrorModel, VideoTask
from app.services.media_io import generate_video
from app.services.status import update_avatar_generation_step_status
from app.workers.queues import JOBS, VIDEO_QUEUE, utcnow


def loop() -> None:
    print("[video-worker] started")
    while True:
        task: VideoTask = VIDEO_QUEUE.get()
        pid = task.promptId
        video_done = False
        video_failure_reported = False
        last_exception: Exception | None = None
        last_failure_message: str | None = None
        max_attempts = 3

        try:
            for attempt in range(1, max_attempts + 1):
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
                        break

                    last_failure_message = "generate_video returned no video path"
                    print(
                        f"[video-worker] video attempt {attempt}/{max_attempts} returned no video for slide {task.slideNo} ({pid})"
                    )

                except Exception as video_exc:
                    last_exception = video_exc
                    last_failure_message = str(video_exc)
                    print(
                        f"[video-worker] video attempt {attempt}/{max_attempts} failed for slide {task.slideNo} ({pid}): {video_exc!r}"
                    )

                if video_done:
                    break

                if attempt < max_attempts:
                    print(
                        f"[video-worker] retrying video generation for slide {task.slideNo} ({pid}) after failure"
                    )

            if not video_done:
                update_avatar_generation_step_status(pid, task.slideNo, video="FAILED")
                video_failure_reported = True
                message = last_failure_message or "Video generation failed"
                if last_exception is not None:
                    raise RuntimeError(message) from last_exception
                raise RuntimeError(message)

        except Exception as e:
            if not video_done and not video_failure_reported:
                update_avatar_generation_step_status(pid, task.slideNo, video="FAILED")
                video_failure_reported = True
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
