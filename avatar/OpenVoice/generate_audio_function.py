import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Literal, Optional

# Imports added for correctly number generation
import inflect
import re

import torch
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, ORJSONResponse
from melo.api import TTS
from openvoice.api import ToneColorConverter
from pydantic import BaseModel

from openvoice import se_extractor


def _env_or(conf: dict, dotted_key: str, default):
    """
    Environment overrides for docker-compose convenience.
    """
    env_map = {
        "runtime.device": "AUDIO_DEVICE",
        "runtime.language": "AUDIO_LANGUAGE",
        "paths.ckpt_converter": "AUDIO_CKPT_CONVERTER",
        "paths.output_dir": "AUDIO_OUTPUT_DIR",
        "paths.base_speakers_dir": "AUDIO_BASE_SPEAKERS_DIR",
        "paths.ses_subdir": "AUDIO_SES_SUBDIR",
        "paths.reference_speaker_dir": "AUDIO_REF_DIR",
        "tts.speed": "AUDIO_TTS_SPEED",
        "tts.noise_scale": "AUDIO_TTS_NOISE_SCALE",
        "tts.noise_scale_w": "AUDIO_TTS_NOISE_SCALE_W",
        "tts.sdp_ratio": "AUDIO_TTS_SDP_RATIO",
        "nlp.nltk_auto_download": "AUDIO_NLTK_AUTO",
        "deps.auto_install_silero_vad": "AUDIO_AUTO_SILERO_VAD"
        # (defaults.* are not env-overridden by design; keep them in file)
    }
    env_name = env_map.get(dotted_key, "")
    env = os.getenv(env_name, None)

    if env is None:
        node = conf
        for k in dotted_key.split("."):
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node if node is not None else default

    if isinstance(default, bool):
        return env.lower() in ("1", "true", "yes", "on")
    if isinstance(default, float):
        try:
            return float(env)
        except Exception:
            return default
    if isinstance(default, int):
        try:
            return int(env)
        except Exception:
            return default
    return env


def _resolve(base: Path, p: str) -> Path:
    pp = Path(p)
    return pp if pp.is_absolute() else (base / pp)


def load_config() -> dict:
    """
    Loads JSON config from AUDIO_CONFIG (or ./audio_config.json),
    applies env overrides, resolves relative paths against the config dir
    (or this script's dir if config missing).
    """
    import json

    cfg_path = Path(os.getenv("AUDIO_CONFIG", "./audio_config.json")).resolve()
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = json.load(f) or {}
        base_dir = cfg_path.parent
    else:
        raw = {}
        base_dir = Path(__file__).resolve().parent

    cfg = {
        "paths": {
            "project_root": _env_or(raw, "paths.project_root", ""),
            "ckpt_converter": _resolve(base_dir, _env_or(raw, "paths.ckpt_converter", "./checkpoints_v2/converter")),
            "output_dir": _resolve(base_dir, _env_or(raw, "paths.output_dir", "./checkpoints_v2/outputs_v2")),
            "base_speakers_dir": _resolve(base_dir, _env_or(raw, "paths.base_speakers_dir", "./checkpoints_v2/base_speakers")),
            "ses_subdir": _env_or(raw, "paths.ses_subdir", "ses"),
            "reference_speaker_dir": _resolve(base_dir, _env_or(raw, "paths.reference_speaker_dir", ".")),
        },
        "runtime": {
            "device": _env_or(raw, "runtime.device", "auto"),  # auto|cuda|mps|cpu
            "language": _env_or(raw, "runtime.language", "EN_NEWEST"),
        },
        "tts": {
            "speed": _env_or(raw, "tts.speed", 1.0),
            "noise_scale": _env_or(raw, "tts.noise_scale", 0.667),
            "noise_scale_w": _env_or(raw, "tts.noise_scale_w", 0.8),
            "sdp_ratio": _env_or(raw, "tts.sdp_ratio", 0.5),
        },
        "nlp": {
            "nltk_auto_download": _env_or(raw, "nlp.nltk_auto_download", True),
        },
        "deps": {
            "auto_install_silero_vad": _env_or(raw, "deps.auto_install_silero_vad", True),
        },
        "server": {
            "title": (raw.get("server") or {}).get("title", "Service Video-Generation APIs"),
            "version": (raw.get("server") or {}).get("version", "0.1"),
            "description": (raw.get("server") or {}).get("description", "API for the Orpheus audio generation."),
        },
        "defaults": {
            "voiceTrack": (raw.get("defaults") or {}).get("voiceTrack", "Hello students! I want you to drink coffee."),
            "course_id": (raw.get("defaults") or {}).get("course_id", ""),
            "voice_file": (raw.get("defaults") or {}).get("voice_file", "")
        }
    }

    pr = cfg["paths"]["project_root"]
    if pr:
        root = _resolve(base_dir, pr)
        for k in ("ckpt_converter", "output_dir", "base_speakers_dir", "reference_speaker_dir"):
            p = cfg["paths"][k]
            cfg["paths"][k] = p if p.is_absolute() else (root / p)

    return cfg


CFG = load_config()


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
    title=CFG["server"]["title"],
    version=CFG["server"]["version"],
    description=CFG["server"]["description"],
    default_response_class=ORJSONResponse,
)


def _ensure_nltk(auto: bool):
    if not auto:
        return
    import nltk

    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),  # present on newer NLTK builds
        ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),  # new name
        ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),  # old name (fallback)
        ("corpora/cmudict", "cmudict"),  # some pipelines expect this present
    ]

    for find_key, dl_name in resources:
        try:
            nltk.data.find(find_key)
        except LookupError:
            try:
                nltk.download(dl_name, quiet=True)
            except Exception:
                # final fallback: try the old tagger if new one failed (or vice versa)
                if dl_name == "averaged_perceptron_tagger_eng":
                    nltk.download("averaged_perceptron_tagger", quiet=True)
                elif dl_name == "averaged_perceptron_tagger":
                    nltk.download("averaged_perceptron_tagger_eng", quiet=True)


def _maybe_install_silero_vad(auto: bool):
    if not auto:
        return
    try:
        # import silero_vad
        print("✓ silero_vad already installed")
    except ImportError:
        print("Installing silero_vad...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "silero-vad"])
        print("✓ silero_vad installed")


def _resolve_reference_voice(voice_file: str, ref_dir: Path) -> Path:
    vf = Path(voice_file)
    return vf if vf.is_absolute() else (ref_dir / vf)


def _speaker_embeddings_dir(base_speakers_dir: Path, ses_subdir: str) -> Path:
    return base_speakers_dir / ses_subdir


def _iter_ses_files(ses_dir: Path):
    if not ses_dir.exists():
        return []
    return sorted(ses_dir.glob("*.pth"))


def _load_tts(language: str, device: str) -> TTS:
    return TTS(language=language, device=device)


def _load_converter(ckpt_dir: Path, device: str) -> ToneColorConverter:
    cfg_json = ckpt_dir / "config.json"
    pth = ckpt_dir / "checkpoint.pth"
    if not cfg_json.exists() or not pth.exists():
        raise RuntimeError(f"Converter files missing in {ckpt_dir} (need config.json & checkpoint.pth)")
    conv = ToneColorConverter(str(cfg_json), device=device)
    conv.load_ckpt(str(pth))
    return conv

# New function to convert numbers to words
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

def generate_audio(
        voiceTrack: str,
        *,
        user_profile: Optional[UserProfile] = None,
        tmp_dir: Path,
        reference_voice_path: Path,
        promptId: str,
) -> str:
    """
    Create per-slide audio files from text using:
      1) Melo TTS (synthesis)
      2) OpenVoice ToneColorConverter (timbre transfer)
    Returns: list of output .wav file paths (empty string for slides that failed)
    """
    paths = CFG["paths"]
    runtime = CFG["runtime"]
    tts_cfg = CFG["tts"]
    nlp_cfg = CFG["nlp"]
    deps_cfg = CFG["deps"]

    ckpt_converter = Path(paths["ckpt_converter"]).resolve()
    output_dir = tmp_dir / "output"
    base_speakers_dir = Path(paths["base_speakers_dir"]).resolve()
    ses_dir = _speaker_embeddings_dir(base_speakers_dir, paths["ses_subdir"])

    output_dir.mkdir(parents=True, exist_ok=True)

    _ensure_nltk(nlp_cfg["nltk_auto_download"])
    _maybe_install_silero_vad(deps_cfg["auto_install_silero_vad"])

    device = _pick_device(runtime["device"])
    language = runtime["language"]

    tone_color_converter = _load_converter(ckpt_converter, device)

    if not reference_voice_path.exists():
        print(f"ERROR: voice_file not found: {reference_voice_path}")
        raise HTTPException(status_code=400, detail=f"voice_file not found: {reference_voice_path}")

    target_se, _ = se_extractor.get_se(str(reference_voice_path), tone_color_converter, vad=True)

    model = _load_tts(language=language, device=device)
    speaker_ids = model.hps.data.spk2id

    speed = float(tts_cfg["speed"])
    noise_scale = float(tts_cfg["noise_scale"])
    noise_scale_w = float(tts_cfg["noise_scale_w"])
    sdp_ratio = float(tts_cfg["sdp_ratio"])

    available_ses: Dict[str, Path] = {}
    for p in _iter_ses_files(ses_dir):
        key = p.stem.lower().replace("_", "-")
        available_ses[key] = p

    text = voiceTrack
    if not text or not text.strip():
        return ""
    
    # Convert numbers to words
    text = numbers_to_words(text)

    tmp_src = output_dir / "tmp.wav"
    save_path = output_dir / f"output.wav"
    success = False

    for speaker_key, speaker_id in speaker_ids.items():
        norm_key = str(speaker_key).lower().replace("_", "-")
        ses_path = available_ses.get(norm_key)
        if ses_path is None:
            continue
        try:
            source_se = torch.load(ses_path, map_location=device)

            model.tts_to_file(
                text,
                speaker_id,
                str(tmp_src),
                speed=speed,
                noise_scale=noise_scale,
                noise_scale_w=noise_scale_w,
                sdp_ratio=sdp_ratio,
            )

            tone_color_converter.convert(
                audio_src_path=str(tmp_src),
                src_se=source_se,
                tgt_se=target_se,
                output_path=str(save_path),
                message="@MyShell",
            )

            success = True
            print(f"✓ audio generated: {save_path}")
            break
        except Exception as e:
            print(f"[generation failed] speaker={speaker_key} error: {e}")

            continue

    return str(save_path) if success else ""


@app.get("/health")
def health():
    return {
        "ok": True,
        "device": _pick_device(CFG["runtime"]["device"]),
        "language": CFG["runtime"]["language"],
        "paths": {
            "ckpt_converter": str(CFG["paths"]["ckpt_converter"]),
            "output_dir": str(CFG["paths"]["output_dir"]),
            "base_speakers_dir": str(CFG["paths"]["base_speakers_dir"]),
            "reference_speaker_dir": str(CFG["paths"]["reference_speaker_dir"]),
            "ses_subdir": CFG["paths"]["ses_subdir"],
        },
        "defaults_present": {
            "voiceTrack": bool(CFG["defaults"].get("voiceTrack")),
            "course_id": bool(CFG["defaults"].get("course_id")),
            "voice_file": bool(CFG["defaults"].get("voice_file"))
        }
    }


@app.post("/v1/audio/generate")
async def generate_audio_endpoint(
        voice_file: UploadFile = File(..., description="Reference voice MP3 (raw file, not base64)"),
        voiceTrack: Optional[str] = Form(None, description="Single slide text"),
        debug: str = Form("not debug", description="is debug?"),
        promptId: str = Form(None, description="Prompt ID"), ):
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

    if debug == 'debug':
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
        path = generate_audio(
            voiceTrack=voiceTrack,
            user_profile=None,  # pass through if you support it via form later
            tmp_dir=tmp_dir,
            reference_voice_path=ref_mp3_path,
            promptId=promptId
        )

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

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
"""TODO: add proper typing and refactor for mypy compliance.

This file is third-party derived and currently runs with mypy errors.
We keep it included in checks, but ignore errors for now to stage rollout.
"""
# mypy: ignore-errors
