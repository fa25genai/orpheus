import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Literal, Optional

import inflect
import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, ORJSONResponse
from pydantic import BaseModel


def _pick_device(pref: str) -> str:
    pref = (pref or "auto").lower()
    if pref == "cuda" and torch.cuda.is_available():
        return "cuda"
    if pref == "mps" and torch.backends.mps.is_available():
        return "mps"
    if pref == "cpu":
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def numbers_to_words(text: str) -> str:
    p = inflect.engine()

    def repl(m):
        s = m.group(0)
        # ordinal numerals like 21st, 3rd
        m_ord = re.fullmatch(r"(\d+)(st|nd|rd|th)", s, re.I)
        if m_ord:
            return p.number_to_words(int(m_ord.group(1)), ordinal=True)
        # decimals or integers
        if "." in s:
            # e.g., 3.14 -> "three point one four"
            return p.number_to_words(s, wantlist=False)
        return p.number_to_words(int(s))

    return re.sub(r"\d+(?:\.\d+)?|(?:\d+(?:st|nd|rd|th))", repl, text)


# =========================
# Pydantic models
# =========================


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
    enrolled_courses: Optional[List[str]] = None


class GenerateAudioRequest(BaseModel):
    voiceTrack: Optional[str] = None
    course_id: Optional[str] = None
    voice_file: Optional[str] = None
    user_profile: Optional[UserProfile] = None


class GenerateAudioResponse(BaseModel):
    audio_file: str


app = FastAPI(
    title="Audio Generation Service",
    version="0.1",
    description="API for Chatterbox-based audio generation",
    default_response_class=ORJSONResponse,
)


def generate_audio(
        voiceTrack: str,
        *,
        user_profile: Optional[UserProfile] = None,
        tmp_dir: Path,
        reference_voice_path: Path,
        promptId: str,
) -> str:
    """
    Create per-slide audio files from text using Chatterbox TTS
    with optional reference voice prompt.
    Returns: path to the generated .wav file (empty string if failed).
    """
    output_dir = tmp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    device = _pick_device("auto")
    print(f"✓ using device: {device}")

    # Load Chatterbox TTS model
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    if not reference_voice_path.exists():
        print(f"ERROR: voice_file not found: {reference_voice_path}")
        raise HTTPException(status_code=400, detail=f"voice_file not found: {reference_voice_path}")

    text = voiceTrack
    if not text or not text.strip():
        return ""

    # Convert numbers to words
    text = numbers_to_words(text)

    save_path = output_dir / "output.wav"

    try:
        # Generate audio with optional voice cloning
        wav = model.generate(
            text,
            audio_prompt_path=str(reference_voice_path),
            language_id="en",
            temperature=0.6,
            top_p=0.9,
            repetition_penalty=2.5,
        )
        ta.save(str(save_path), wav, model.sr)

        print(f"✓ audio generated: {save_path}")
        return str(save_path)
    except Exception as e:
        print(f"[generation failed] error: {e}")
        return ""


@app.get("/health")
def health():
    return {
        "ok": True,
        "device": _pick_device("auto"),
        "language": "en",
    }


@app.post("/v1/audio/generate")
async def generate_audio_endpoint(
        voice_file: UploadFile = File(..., description="Reference voice MP3 (raw file, not base64)"),
        voiceTrack: Optional[str] = Form(None, description="Single slide text"),
        debug: str = Form("not debug", description="is debug?"),
        promptId: str = Form(None, description="Prompt ID"),
):
    """
    Accepts multipart/form-data:
      - voice_file: MP3 file upload
      - voiceTrack: string with content
      - course_id: optional (falls back to config default)

    Returns the first generated WAV as a binary response (audio/wav).
    """

    print(f"✓ request: voice_file={voice_file.filename} voiceTrack={'[present]' if voiceTrack else '[missing]'} debug={debug} promptId={promptId or '[none]'}")

    # Resolve texts
    if not voiceTrack:
        raise HTTPException(status_code=400, detail="Provide 'voiceTrack' input.")

    if debug == "debug":
        mock_path = Path(os.getenv("VOICE_GEN_DEBUG_WAV_PATH", "./debug/mock.wav"))
        return FileResponse(
            path=str(mock_path),
            media_type="audio/wav",
            filename=mock_path.name,
            headers={"Cache-Control": "no-store"},
            # background tasks are not used in debug mode
        )

    # Save uploaded MP3 to a temp path
    tmp_dir = Path(tempfile.mkdtemp(prefix="audio_gen_"))
    print(f"✓ created temp dir {tmp_dir}")
    ref_mp3_path = tmp_dir / "reference.mp3"

    def _cleanup():
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
                print(f"✓ cleaned up temp dir {tmp_dir}")
        except Exception:
            pass

    try:
        with ref_mp3_path.open("wb") as out_f:
            while True:
                chunk = await voice_file.read(1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)
        print(f"✓ saved uploaded voice_file to {ref_mp3_path}")

        # Call your internal generator (expects a file path for reference voice)
        path = generate_audio(voiceTrack=voiceTrack, user_profile=None, tmp_dir=tmp_dir, reference_voice_path=ref_mp3_path, promptId=promptId)

        if not path:
            _cleanup()
            print("ERROR: audio generation produced no files.")
            raise HTTPException(status_code=500, detail="Audio generation produced no files.")

        background = BackgroundTasks()
        background.add_task(_cleanup)

        # Stream WAV back to the client
        return FileResponse(
            path=str(path),
            media_type="audio/wav",
            filename=path,
            headers={"Cache-Control": "no-store"},
            background=background,
        )

    except HTTPException:
        # Re-raise FastAPI errors untouched
        _cleanup()
        print("ERROR: audio generation failed with HTTPException.")
        raise
    except Exception as e:
        # Cleanup temp dir on error
        _cleanup()
        print(f"ERROR: audio generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("generate_audio:app", host="0.0.0.0", port=8000, reload=True)
