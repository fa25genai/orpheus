from fastapi import FastAPI, HTTPException, status
import uuid
from models import PromptResponse, PromptRequest, DataResponse
import redis
from enum import Enum
import json

API_METADATA = {
    "title": "Orpheus CoreAI-Service API",
    "version": "0.1.0",
    "description": """
    API for the Orpheus core orchestration.
    From the repository: "The Orpheus System transforms static slides into interactive lecture videos with lifelike professor avatars, combining expressive narration, visual presence, and dynamic content to create engaging, personalized learning experiences."
    """,
    "terms_of_service": "https://github.com/fa25genai/orpheus",
    "contact": {
        "name": "Orpheus Project",
        "url": "https://github.com/fa25genai/orpheus/issues/new",
    },
    "license_info": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
}

TAGS_METADATA = [
    {
        "name": "core",
        "description": "Endpoints for core AI",
    }
]

try:
    lecture_store = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    lecture_store.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    lecture_store = None

class JobStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

app = FastAPI(
    openapi_tags=TAGS_METADATA,
    **API_METADATA
)

@app.post(
    "/core/prompt",
    tags=["core"],
    summary="Submit a prompt to generate a lecture",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PromptResponse
)
async def create_lecture_from_prompt(request: PromptRequest):
    if not lecture_store:
        raise HTTPException(status_code=503, detail="Redis service is unavailable.")

    lecture_id = uuid.uuid4()

    lecture_data = {
        "status": JobStatus.PROCESSING.value,
        "slidesUrl": None,
        "videoUrl": None
    }
    
    lecture_store.set(str(lecture_id), json.dumps(lecture_data))
    
    return PromptResponse(lectureId=lecture_id)

@app.get(
    "/core/slides/{lectureId}",
    tags=["core"],
    summary="Get the generated slides",
    response_model=DataResponse
)
def get_slides_by_lecture_id(lectureId: uuid.UUID):
    if not lecture_store:
        raise HTTPException(status_code=503, detail="Redis service is unavailable.")

    job_data_str = lecture_store.get(str(lectureId))
    if not job_data_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lecture job found with the provided ID."
        )
    
    job = json.loads(job_data_str)
    
    job["status"] = JobStatus.COMPLETED.value
    job["slidesUrl"] = f"https://storage.example.com/slides/{lectureId}.pptx"

    lecture_store.set(str(lectureId), json.dumps(job))

    return DataResponse(status=job["status"], slidesUrl=job.get("slidesUrl"))

@app.get(
    "/core/video/{lectureId}",
    tags=["core"],
    summary="Get the generated video",
    response_model=DataResponse
)
def get_video_by_lecture_id(lectureId: uuid.UUID):
    if not lecture_store:
        raise HTTPException(status_code=503, detail="Redis service is unavailable.")
        
    job_data_str = lecture_store.get(str(lectureId))
    if not job_data_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lecture job found with the provided ID."
        )
    
    job = json.loads(job_data_str)

    job["status"] = JobStatus.COMPLETED.value
    job["videoUrl"] = f"https://storage.example.com/videos/{lectureId}.mp4"

    lecture_store.set(str(lectureId), json.dumps(job))

    return DataResponse(status=job["status"], videoUrl=job.get("videoUrl"))
