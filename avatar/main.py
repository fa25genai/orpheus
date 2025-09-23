from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict
from uuid import UUID

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, Field, UUID4, constr

app = FastAPI(
    title="Service Video-Generation APIs",
    version="0.1",
    description=(
        "API for the Orpheus video generation. Transforms fluent texts into "
        "interactive lecture videos with lifelike professor avatars."
    ),
)

# ---------------------------
# Pydantic models (from spec)
# ---------------------------

class Preferences(BaseModel):
    answerLength: Optional[Literal["short", "medium", "long"]] = None
    languageLevel: Optional[Literal["basic", "intermediate", "advanced"]] = None
    expertiseLevel: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = None
    includePictures: Optional[Literal["none", "few", "many"]] = None

class UserProfile(BaseModel):
    id: str
    role: Literal["student", "instructor"]
    language: Literal["german", "english"]
    preferences: Optional[Preferences] = None
    enrolledCourses: Optional[List[str]] = None

class GenerateRequest(BaseModel):
    #slideMessages: List[constr(min_length=1)] = Field(..., min_items=1)
    lectureId: UUID4
    courseId: str
    userProfile: UserProfile

class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None

class GenerationAcceptedResponse(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    createdAt: datetime

class GenerationStatusResponse(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    error: Optional[ErrorModel] = None

# ---------------------------
# In-memory job store
# ---------------------------

class Job(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    error: Optional[ErrorModel] = None

JOBS: Dict[UUID, Job] = {}  # simple in-memory cache; replace with Redis/DB in prod

# ---------------------------
# Your generation functions
# ---------------------------
# imports for TTS pipeline
import os
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
import nltk
from melo.api import TTS

slide_texts = ["Welcome to the course on AI.", "In this slide, we will discuss machine learning."]
course_id = "course123"
voice_file = "kursche_voice.mp3"  # Path to a default voice file
def generate_audio(
    slide_texts: List[str],
    *,
    course_id: str,
    user_profile: UserProfile = None,
    voice_file: str
) -> List[str]:
    """
    Create per-slide audio files from text.

    Returns a list of file paths (one per slide).
    Replace the body with your TTS pipeline (e.g., Coqui, ElevenLabs, local TTS).
    """
    # TODO: implement real TTS.
    # For now, pretend we produced audio files:
    # Defining paths
   # Get the directory where THIS SCRIPT is located (not the current working directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Script directory: {script_dir}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Define ALL paths relative to the SCRIPT directory
    base_dir = script_dir  # This is the key fix!
    
    ckpt_converter = os.path.join(base_dir,"OpenVoice", "checkpoints_v2", "converter")
    output_dir = os.path.join(base_dir,"OpenVoice", "checkpoints_v2", "outputs_v2")
    base_speakers_dir = os.path.join(base_dir,"OpenVoice", "checkpoints_v2", "base_speakers")
    reference_speaker_dir = os.path.join(base_dir, "OpenVoice")
    ses_dir = os.path.join(base_speakers_dir, "ses")
    
    # Also make the voice file path absolute relative to script directory
    reference_speaker = os.path.join(reference_speaker_dir, voice_file)
    
    print(f"Looking for config at: {os.path.join(ckpt_converter, 'config.json')}")
    print(f"Config exists: {os.path.exists(os.path.join(ckpt_converter, 'config.json'))}")
    print(f"Voice file exists: {os.path.exists(reference_speaker)}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)

    # Set device
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    # Initialize ToneColorConverter
    tone_color_converter = ToneColorConverter(os.path.join(ckpt_converter, "config.json"), device=device)
    tone_color_converter.load_ckpt(os.path.join(ckpt_converter, "checkpoint.pth"))

    try:
        import silero_vad
        print("✓ silero_vad is already installed")
    except ImportError:
        print("Installing silero_vad...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "silero-vad"])
        print("✓ silero_vad installed successfully")
        
    # Extract speaker embedding
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, vad=True)

    # TTS parameters
    speed = 1.0
    noise_scale = 0.667
    noise_scale_w = 0.8
    sdp_ratio = 0.5

    audio_paths = []
    
    # Process each slide text
    for i, text in enumerate(slide_texts):
        if not text.strip():  # Skip empty texts
            audio_paths.append("")
            continue
            
        # Generate audio for this slide
        # Choosing a language/model based on user profile could be added here
        language = 'EN_NEWEST'
        model = TTS(language=language, device=device)
        speaker_ids = model.hps.data.spk2id
        
        src_path = os.path.join(output_dir, f"tmp_{i}.wav")
        success = False
        
        # Try different speakers until one works
        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            normalized_speaker_key = speaker_key.lower().replace('_', '-')
            # Adjust the path as necessary
            ses_file_path = os.path.join(ses_dir, f"{normalized_speaker_key}.pth")
            
            if not os.path.exists(ses_file_path):
                continue
                
            try:
                source_se = torch.load(ses_file_path, map_location=device)
                
                # Generate base audio with given parameters
                model.tts_to_file(
                    text, 
                    speaker_id, 
                    src_path, 
                    speed=speed,
                    noise_scale=noise_scale,
                    noise_scale_w=noise_scale_w,
                    sdp_ratio=sdp_ratio
                )
                
                # Generate final output filename
                output_filename = f"{course_id}_slide_{i+1}.wav"
                save_path = os.path.join(output_dir, output_filename)
                
                # Convert voice
                tone_color_converter.convert(
                    audio_src_path=src_path, 
                    src_se=source_se, 
                    tgt_se=target_se, 
                    output_path=save_path,
                    message="@MyShell"
                )
                
                audio_paths.append(save_path)
                success = True
                print(f"✓ Generated audio for slide {i+1}: {save_path}")
                break  # Success, move to next slide
                
            except Exception as e:
                print(f"Error with speaker {speaker_key} for slide {i+1}: {e}")
                continue
        
        if not success:
            print(f"Failed to generate audio for slide {i+1}")
            audio_paths.append("")  # Add empty string for failed generation
            
        # Clean up temporary file
        try:
            if os.path.exists(src_path):
                os.remove(src_path)
        except:
            pass

    return audio_paths
    #audio_paths = [f"/tmp/{course_id}_slide_{i+1}.wav" for i, _ in enumerate(slide_texts)]
    
audio_outputs = generate_audio(
    slide_texts,
    course_id=course_id,
    voice_file=voice_file
)
print("Generated audio files:", audio_outputs)

def generate_video(
    slide_texts: List[str],
    audio_paths: List[str],
    *,
    lecture_id: UUID4,
    course_id: str,
    user_profile: UserProfile,
) -> str:
    """
    Assemble the final video using the audio tracks and slide content.

    Returns the path to the rendered video file.
    Replace with your real compositor (e.g., moviepy/ffmpeg + avatar renderer).
    """
    # TODO: implement real video assembly.
    video_path = f"/tmp/{lecture_id}_final.mp4"
    return video_path

# ---------------------------
# Background job runner
# ---------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def process_generation(payload: GenerateRequest) -> None:
    """Runs the end-to-end pipeline; updates JOBS accordingly."""
    try:
        # 1) Audio
        audio_paths = generate_audio(
            payload.slideMessages,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        # 2) Video
        _ = generate_video(
            payload.slideMessages,
            audio_paths,
            lecture_id=payload.lectureId,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        # 3) Mark as done
        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="DONE",
            lastUpdated=_utcnow(),
            error=None,
        )
    except Exception as exc:
        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="FAILED",
            lastUpdated=_utcnow(),
            error=ErrorModel(code="GENERATION_FAILED", message=str(exc)),
        )

# ---------------------------
# Routes
# ---------------------------

@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={
        400: {"model": ErrorModel},
        401: {"model": ErrorModel},
        500: {"model": ErrorModel},
    },
)
def request_video_generation(payload: GenerateRequest, background: BackgroundTasks, response: Response):
    # (Optional) idempotency: if a job with the same lectureId exists and is IN_PROGRESS/DONE, you could short-circuit here.
    now = _utcnow()
    JOBS[payload.lectureId] = Job(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        lastUpdated=now,
        error=None,
    )

    # Kick off background processing
    background.add_task(process_generation, payload)

    # Set Location header to the status endpoint
    response.headers["Location"] = f"/v1/video/{payload.lectureId}/status"

    return GenerationAcceptedResponse(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        createdAt=now,
    )

@app.get(
    "/v1/video/{lectureId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
)
def get_generation_status(lectureId: UUID4):
    job = JOBS.get(lectureId)
    if not job:
        raise HTTPException(status_code=404, detail="Request not found")
    return GenerationStatusResponse(
        lectureId=job.lectureId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        error=job.error,
    )

# ---------------------------
# Entry point
# ---------------------------

# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
