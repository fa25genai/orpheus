import os
import sys
from pathlib import Path
from typing import List, Optional, Literal, Dict

import torch
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import ORJSONResponse, FileResponse
from pydantic import BaseModel

from melo.api import TTS
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

import tempfile
import shutil


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
            "slide_texts": (raw.get("defaults") or {}).get("slide_texts", []),
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
    slide_texts: Optional[List[str]] = None
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


def generate_audio(
        slide_texts: List[str],
        *,
        course_id: str,
        user_profile: Optional[UserProfile] = None,
        reference_voice_path: Path,
) -> List[str]:
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
    output_dir = Path("./output").resolve()
    base_speakers_dir = Path(paths["base_speakers_dir"]).resolve()
    ses_dir = _speaker_embeddings_dir(base_speakers_dir, paths["ses_subdir"])
    ref_dir = Path(paths["reference_speaker_dir"]).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    _ensure_nltk(nlp_cfg["nltk_auto_download"])
    _maybe_install_silero_vad(deps_cfg["auto_install_silero_vad"])

    device = _pick_device(runtime["device"])
    language = runtime["language"]

    tone_color_converter = _load_converter(ckpt_converter, device)

    if not reference_voice_path.exists():
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

    audio_paths: List[str] = []

    for i, text in enumerate(slide_texts):
        if not text or not text.strip():
            audio_paths.append("")
            continue

        tmp_src = output_dir / f"tmp_{i}.wav"
        save_path = output_dir / f"{course_id}_slide_{i + 1}.wav"
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

                audio_paths.append(str(save_path))
                success = True
                print(f"✓ slide {i + 1}: {save_path}")
                break

            except Exception as e:
                print(f"[slide {i + 1}] speaker={speaker_key} failed: {e}")
                continue

        if not success:
            print(f"✗ slide {i + 1}: generation failed")
            audio_paths.append("")

        try:
            if tmp_src.exists():
                tmp_src.unlink()
        except Exception:
            pass

    return audio_paths


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
            "slide_texts": bool(CFG["defaults"].get("slide_texts")),
            "course_id": bool(CFG["defaults"].get("course_id")),
            "voice_file": bool(CFG["defaults"].get("voice_file"))
        }
    }


@app.post("/v1/audio/generate")
async def generate_audio_endpoint(
        voice_file: UploadFile = File(..., description="Reference voice MP3 (raw file, not base64)"),
        # Prefer slide_texts list; accept a single slide_text for convenience
        slide_texts: Optional[List[str]] = Form(None, description="One or more slide texts"),
        slide_text: Optional[str] = Form(None, description="Single slide text (alternative to slide_texts)"),
        # Optional: allow course_id to be omitted; fall back to config default if needed
        course_id: Optional[str] = Form(None),
        debug: str = Form("not debug", description="is debug?")):
    """
    Accepts multipart/form-data:
      - voice_file: MP3 file upload
      - slide_texts: repeated form field (or 'slide_text' once)
      - course_id: optional (falls back to config default)

    Returns the first generated WAV as a binary response (audio/wav).
    """

    # Resolve texts
    if (not slide_texts or len(slide_texts) == 0) and not slide_text:
        # fallback to CFG default only if you want; else require at least one text
        default_texts = CFG["defaults"].get("slide_texts", [])
        if not default_texts:
            raise HTTPException(status_code=400, detail="Provide 'slide_texts' (can be repeated) or 'slide_text'.")
        slide_texts = default_texts
    elif not slide_texts:
        slide_texts = [slide_text]

    if not isinstance(slide_texts, list) or not all(isinstance(x, str) for x in slide_texts):
        raise HTTPException(status_code=400, detail="'slide_texts' must be a list of strings.")

    # Resolve course_id (optional -> default)
    if not course_id:
        course_id = CFG["defaults"].get("course_id", "")
        # You can enforce it if absolutely required:
        # if not course_id:
        #     raise HTTPException(status_code=400, detail="course_id is required (provide or set default in config).")

    if debug == 'debug':
        mock_path = Path(os.getenv("VOICE_GEN_DEBUG_WAV_PATH", "./debug/mock.wav"))
        return FileResponse(
            path=str(mock_path),
            media_type="audio/wav",
            filename=mock_path.name,
            headers={"Cache-Control": "no-store"},
            background=background,
        )
    # Save uploaded MP3 to a temp path
    tmp_dir = Path(tempfile.mkdtemp(prefix="audio_gen_"))
    ref_mp3_path = tmp_dir / "reference.mp3"
    try:
        with ref_mp3_path.open("wb") as out_f:
            while True:
                chunk = await voice_file.read(1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)

        # Call your internal generator (expects a file path for reference voice)
        # NOTE: this is your existing backend function you already have.
        paths = generate_audio(
            slide_texts=slide_texts,
            course_id=course_id,
            user_profile=None,  # pass through if you support it via form later
            reference_voice_path=ref_mp3_path,
        )

        # Pick the first valid WAV produced
        first_path = next((Path(p) for p in paths if p and Path(p).exists()), None)
        if not first_path:
            raise HTTPException(status_code=500, detail="Audio generation produced no files.")

        # Schedule temp cleanup after the response is sent
        def _cleanup():
            try:
                # If your output WAV is meant to be ephemeral, you can delete it here too:
                # if first_path.exists(): first_path.unlink(missing_ok=True)
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

        background = BackgroundTasks()
        background.add_task(_cleanup)

        # Stream WAV back to the client
        return FileResponse(
            path=str(first_path),
            media_type="audio/wav",
            filename=first_path.name,
            headers={"Cache-Control": "no-store"},
            background=background,
        )

    except HTTPException:
        # Re-raise FastAPI errors untouched
        raise
    except Exception as e:
        # Cleanup temp dir on error
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
