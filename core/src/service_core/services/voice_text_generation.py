# voice_transcript_generator.py
# ---------------------------------------------------------
# FastAPI microservice that generates FRIENDLY narration text per slide by
# combining:
#   - DI data (Document Intelligence snippets/images/meta)
#   - Slides Team data (slides with bullets/notes)
#   - User profile/persona
#
# NO audio. NO timing. NO markers. NO mock LLM.
# Uses a LOCAL Transformers LLM (instruct model) to decide content/style/length.
#
# ▶ Install:
#   pip install fastapi pydantic uvicorn
#   pip install --upgrade transformers accelerate sentencepiece torch
#
# ▶ Run:
#   uvicorn voice_transcript_generator:app --reload --port 8082
#
# ▶ Slim Output Endpoints:
#   POST /v1/voice_transcript/ingest_slim   (raw team schemas → slim output)
#   POST /v1/voice_transcript/slim          (canonical input → slim output)
# ---------------------------------------------------------

from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
import re
import uuid
import datetime as dt
from collections import Counter
import json as _json

# =========================
# Local Transformers LLM (required; no mock fallback)
# =========================

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    _TRANSFORMERS_AVAILABLE = True
except Exception as e:
    _TRANSFORMERS_AVAILABLE = False
    _TRANSFORMERS_IMPORT_ERROR = e

class LocalLLMClient:
    """
    Local JSON-decider & micro-writer using a public instruct model.
    No API key needed. Runs offline after first model download.
    """
    def __init__(
        self,
        model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # CPU-friendly; change if you have a GPU
        dtype: str = "float32",                            # "float16"/"bfloat16" if you have GPU
        device_map: str = "mps",
        max_new_tokens: int = 384,
        temperature: float = 0.2
    ):
        if not _TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                f"Transformers not available: {_TRANSFORMERS_IMPORT_ERROR}\n"
                "Install with: pip install --upgrade transformers accelerate sentencepiece torch"
            )
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        torch_dtype = getattr(torch, dtype) if dtype in ("float16", "bfloat16", "float32") else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch_dtype, device_map=device_map)
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        import re
        prompt = (
            f"<<SYS>>{system_prompt}\n"
            "Return ONLY valid JSON. No prose, no markdown.\n"
            "JSON must match this schema (not enforced, just a hint):\n"
            f"{_json.dumps(schema_hint)}\n<</SYS>>\n\n"
            f"{user_prompt}\n\nJSON:"
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        out = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=self.temperature > 0,
            eos_token_id=self.tokenizer.eos_token_id
        )
        text = self.tokenizer.decode(out[0], skip_special_tokens=True)
        # Try to extract the first {...} block using regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return _json.loads(match.group(0))
            except Exception as e:
                print("[LLM JSON ERROR]", e, "\nRaw output:\n", text)
        # Fallback: print and return error info
        print("[LLM JSON ERROR] Could not parse JSON. Raw output:\n", text)
        return {"error": "LLM did not return valid JSON", "raw": text}

# Instantiate the local LLM (fail early if missing)
# TIP: If you have a GPU, you can switch to "mistralai/Mistral-7B-Instruct" and dtype="float16"
LLM = LocalLLMClient(
    model="mistralai/Mistral-7B-Instruct",  # Instruction-tuned, MPS-compatible
    dtype="float16",     # Use float32 for best MPS compatibility
    device_map="cuda",    # Use CUDA GPU
    max_new_tokens=128,   # Reasonable length for chat
    temperature=0.2
)

# =========================
# Canonical Data Models (input)
# =========================

class Persona(BaseModel):
    grade_level: Literal["middle", "high", "undergrad", "grad", "professional"] = "high"
    language: Literal["en", "de"] = "en"
    style: Literal["friendly-concise", "friendly-detailed", "enthusiastic", "neutral"] = "friendly-concise"
    region: Optional[str] = None
    learning_focus: Optional[Literal["big-picture", "step-by-step", "definitions-first"]] = "step-by-step"
    pace_wpm: int = Field(145, ge=100, le=220)  # kept for completeness; not used in slim output

class DIImageRef(BaseModel):
    id: str
    caption: Optional[str] = None
    tags: Optional[List[str]] = None

class DISnippet(BaseModel):
    id: str
    text: str
    source: Optional[str] = None
    score: Optional[float] = None
    tags: Optional[List[str]] = None
    images: Optional[List[DIImageRef]] = None

class DIData(BaseModel):
    snippets: List[DISnippet] = []

class ImageBrief(BaseModel):
    type: Optional[Literal["diagram", "photo", "chart", "illustration"]] = None
    description: Optional[str] = None
    source_hints: Optional[List[str]] = None

class SlideSpec(BaseModel):
    index: int
    title: str
    bullets: List[str]
    image_brief: Optional[ImageBrief] = None
    speaker_notes: Optional[str] = None

class SlidesTeamData(BaseModel):
    slides: List[SlideSpec]

class VoiceTranscriptSlimRequest(BaseModel):
    user_profile: Persona
    di_data: DIData
    slide_team_data: SlidesTeamData
    lecture_id: Optional[str] = None

# =========================
# RAW Schemas (as-provided) — for ingest_slim endpoint
# =========================

class RawUserPreferences(BaseModel):
    answerLength: Optional[Literal["short", "medium", "long"]] = "medium"
    languageLevel: Optional[Literal["basic", "intermediate", "advanced"]] = "intermediate"
    expertiseLevel: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = "beginner"
    includePictures: Optional[Literal["none", "few", "many"]] = "few"

class RawUserProfile(BaseModel):
    id: Optional[str] = "user"
    role: Optional[Literal["student", "instructor"]] = "student"
    language: Optional[Literal["german", "english"]] = "english"
    preferences: Optional[RawUserPreferences] = RawUserPreferences()
    enrolledCourses: Optional[List[str]] = []

class RawDIQuery(BaseModel):
    courseId: Optional[str] = None
    query: Optional[str] = None

class RawDIImages(BaseModel):
    image: Optional[str] = None
    desc: Optional[str] = None
    textualDescription: Optional[str] = None

class RawDIContent(BaseModel):
    content: Optional[List[str]] = None
    images: Optional[Any] = None  # can be dict or list; we normalize later

class RawSlidesAsset(BaseModel):
    name: Optional[str] = None
    assetDesc: Optional[str] = None
    mimetype: Optional[str] = None
    data: Optional[str] = None

class RawSlidesScript(BaseModel):
    courseId: Optional[str] = None
    lectureId: Optional[str] = None
    lectureScript: Optional[str] = None
    assets: Optional[List[RawSlidesAsset]] = None

class RawSlidesDeckSlide(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class RawSlidesDeck(BaseModel):
    title: Optional[str] = None
    slides: Optional[List[RawSlidesDeckSlide]] = None

class IngestSlimRequest(BaseModel):
    userProfile: RawUserProfile
    diTeamMeta: Optional[RawDIQuery] = None
    diTeamContent: RawDIContent
    slidesTeamScript: Optional[RawSlidesScript] = None
    slidesTeamDeck: RawSlidesDeck
    lectureId: Optional[str] = None  # override if provided

    @field_validator("slidesTeamDeck")
    @classmethod
    def validate_deck_has_slides(cls, v):
        if not v or not v.slides:
            raise ValueError("slidesTeamDeck.slides is required and must be non-empty")
        return v

# =========================
# Slim Output Model
# =========================

class VoiceTranscriptSlimResponse(BaseModel):
    lectureId: str
    slideMessages: List[str]
    userProfile: Dict[str, Any]

# =========================
# Helpers (keywords & relevance)
# =========================

_WORD_RE = re.compile(r"\b\w[\w'-]*\b")

def keywords_from(text: str, top_k: int = 10) -> List[str]:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    words = [w for w in words if len(w) > 2]
    common = Counter(words).most_common(top_k)
    return [w for w, _ in common]

def relevance(slide: SlideSpec, snippet: DISnippet) -> float:
    slide_text = " ".join([slide.title] + slide.bullets + ([slide.speaker_notes] if slide.speaker_notes else []))
    kws_slide = set(keywords_from(slide_text, 14))
    kws_snip = set(keywords_from(snippet.text, 14)) | set(snippet.tags or [])  # fixed union
    if not kws_snip:
        return 0.0
    overlap = len(kws_slide & kws_snip) / len(kws_snip)
    if snippet.score is not None:
        overlap = 0.6 * overlap + 0.4 * float(snippet.score)
    return overlap

def clamp_sentence(s: str, max_words: int = 22) -> str:
    tokens = s.strip().split()
    if len(tokens) <= max_words:
        s = s.strip()
        return s if s.endswith((".", "!", "?")) else s + "."
    return " ".join(tokens[:max_words]) + "…"

def build_raw_profile_for_llm_from_persona(persona: Persona) -> Dict[str, Any]:
    """
    Minimal raw-like profile so LLM can reason consistently.
    Tune defaults if you persist richer prefs elsewhere.
    """
    return {
        "language": "english" if persona.language == "en" else "german",
        "preferences": {
            "answerLength": "medium",
            "languageLevel": "intermediate",
            "expertiseLevel": "beginner" if persona.style != "neutral" else "advanced",
            "includePictures": "few"
        }
    }

# =========================
# LLM decision helpers
# =========================

def llm_plan_for_slide(slide: SlideSpec, user_profile_raw: Dict[str, Any], di: DIData) -> Dict[str, Any]:
    """
    Ask LLM which DI snippets to include and how many sentences/style to use.
    Returns dict:
      { selected_snippet_ids: [...], sentence_count: int (2..4), style: "...", include_visual_callouts: bool }
    """
    system = (
        "You are a precise content selector for slide narration. "
        "Choose the most relevant DI facts that support the slide text, respect the user profile, "
        "and output JSON only."
    )
    di_small = []
    for sn in di.snippets[:6]:
        di_small.append({
            "id": sn.id,
            "text": (sn.text[:220] + "…") if len(sn.text) > 220 else sn.text,
            "score": float(sn.score) if sn.score is not None else 0.5,
            "tags": sn.tags or []
        })
    schema_hint = {
        "type": "object",
        "properties": {
            "selected_snippet_ids": {"type": "array", "items": {"type": "string"}},
            "sentence_count": {"type": "integer", "minimum": 2, "maximum": 4},
            "style": {"type": "string", "enum": ["friendly-concise","friendly-detailed","enthusiastic","neutral"]},
            "include_visual_callouts": {"type": "boolean"},
            "reasons": {"type": "string"}
        },
        "required": ["selected_snippet_ids","sentence_count","style","include_visual_callouts"]
    }
    user_payload = {
        "user_profile": user_profile_raw,
        "slide": {"title": slide.title, "bullets": slide.bullets, "speaker_notes": slide.speaker_notes},
        "di_snippets": di_small
    }
    user_prompt = (
        "Decide DI facts and narration style/length for this slide.\n"
        "RULES:\n"
        "- Slide text is the backbone; DI augments and must not contradict.\n"
        "- Beginners: friendly-concise; Advanced/Expert: neutral.\n"
        "- answerLength short/medium/long → 2-3 / 3 / 3-4 sentences respectively.\n"
        "- If includePictures == none → include_visual_callouts=false.\n"
        "Return JSON only.\n"
        "DATA:\n" + _json.dumps(user_payload)
    )
    return LLM.complete_json(system, user_prompt, schema_hint)

def llm_write_slide_text(slide: SlideSpec, user_profile_raw: Dict[str, Any], selected_snips: List[DISnippet], sentence_count: int, style: str) -> str:
    """
    Ask LLM to write the actual narration text for the slide (single paragraph),
    using the slide title+bullets as backbone + selected DI facts. 2–4 sentences.
    """
    system = (
        "You are a friendly instructional narrator. Write clear, concise slide narration. "
        "2–4 sentences total, each ≤ 22 words. Use plain language, keep code tokens intact."
    )
    di_texts = [sn.text for sn in selected_snips]
    user_payload = {
        "user_profile": user_profile_raw,
        "style": style,
        "sentence_count": max(2, min(4, int(sentence_count))),
        "slide": {"title": slide.title, "bullets": slide.bullets, "speaker_notes": slide.speaker_notes},
        "di_facts": di_texts
    }
    schema_hint = {
        "type": "object",
        "properties": { "text": {"type": "string"} },
        "required": ["text"]
    }
    user_prompt = (
        "Write the narration paragraph now.\n"
        "Constraints:\n"
        f"- Style: {style}\n"
        "- 2–4 sentences total, each ≤ 22 words.\n"
        "- Use slide bullets as backbone; add selected DI facts only if they help.\n"
        "- No lists, no markdown, no headings; return plain text.\n"
        "DATA:\n" + _json.dumps(user_payload)
    )
    out = LLM.complete_json(system, user_prompt, schema_hint)
    text = out.get("text", "").strip()
    # Ensure ending punctuation
    if text and text[-1] not in ".!?":
        text += "."
    return text

# =========================
# Adapters (RAW → Canonical)
# =========================

def map_user_profile_to_persona(up: RawUserProfile) -> Persona:
    lang = (up.language or "english").lower()
    prefs = up.preferences or RawUserPreferences()
    level = prefs.languageLevel or "intermediate"
    expertise = prefs.expertiseLevel or "beginner"

    style = "friendly-concise"
    if expertise in ("advanced", "expert"):
        style = "neutral"

    return Persona(
        grade_level="high",
        language="en" if lang.startswith("english") else "de",
        style=style,
        learning_focus="step-by-step",
        pace_wpm=145  # not used in slim mode
    )

def map_di_raw_to_canonical(di_content: RawDIContent) -> DIData:
    snippets: List[DISnippet] = []
    if di_content and di_content.content:
        for i, text in enumerate(di_content.content, start=1):
            if isinstance(text, str) and text.strip():
                snippets.append(DISnippet(id=f"di_c{i}", text=text.strip(), score=0.7))
    # images normalization skipped, not needed for narration text
    return DIData(snippets=snippets)

def map_slides_raw_to_canonical(deck: RawSlidesDeck) -> SlidesTeamData:
    slides: List[SlideSpec] = []
    for idx, s in enumerate(deck.slides or [], start=1):
        title = s.title or f"Slide {idx}"
        content = s.content or ""
        bullets = [content] if content else []
        slides.append(SlideSpec(index=idx, title=title, bullets=bullets))
    return SlidesTeamData(slides=slides)

def raw_profile_dict(up: RawUserProfile) -> Dict[str, Any]:
    return {
        "id": up.id,
        "role": up.role,
        "language": up.language,
        "preferences": (up.preferences.dict() if isinstance(up.preferences, RawUserPreferences) else (up.preferences or {})),
        "enrolledCourses": up.enrolledCourses or []
    }

# =========================
# Core: generate slide messages (no timing/markers)
# =========================

def generate_slide_messages(
    di_data: DIData,
    slides_data: SlidesTeamData,
    user_profile_raw: Dict[str, Any]
) -> List[str]:
    messages: List[str] = []
    for slide in slides_data.slides:
        # plan with LLM
        plan = llm_plan_for_slide(slide, user_profile_raw, di_data)
        chosen_ids = set(plan.get("selected_snippet_ids", []))
        sentence_count = int(plan.get("sentence_count", 3))
        style = plan.get("style", "friendly-concise")

        # pick selected DI snippets (preserve order by relevance)
        ranked = sorted(di_data.snippets, key=lambda sn: relevance(slide, sn), reverse=True)
        selected = [sn for sn in ranked if sn.id in chosen_ids]
        # write narration with LLM
        text = llm_write_slide_text(slide, user_profile_raw, selected, sentence_count, style)
        messages.append(text)
    return messages

# =========================
# FastAPI
# =========================

app = FastAPI(title="Voice Transcript Generator (Slim Text Only, Local LLM)", version="2.0.0")

@app.post("/v1/voice_transcript/slim", response_model=VoiceTranscriptSlimResponse)
def voice_transcript_slim(req: VoiceTranscriptSlimRequest):
    if not req.slide_team_data.slides:
        raise HTTPException(status_code=400, detail="slide_team_data.slides is required")

    # Build a raw-like profile for the LLM from Persona
    raw_for_llm = build_raw_profile_for_llm_from_persona(req.user_profile)

    slide_messages = generate_slide_messages(
        di_data=req.di_data,
        slides_data=req.slide_team_data,
        user_profile_raw=raw_for_llm
    )

    lecture_id = req.lecture_id or f"lec-{uuid.uuid4()}"
    return VoiceTranscriptSlimResponse(
        lectureId=lecture_id,
        slideMessages=slide_messages,
        userProfile=raw_for_llm
    )

@app.post("/v1/voice_transcript/ingest_slim", response_model=VoiceTranscriptSlimResponse)
def voice_transcript_ingest_slim(raw: IngestSlimRequest):
    # Persona + raw profile
    persona = map_user_profile_to_persona(raw.userProfile)
    raw_profile = raw_profile_dict(raw.userProfile)

    # DI + Slides
    di_data = map_di_raw_to_canonical(raw.diTeamContent)
    slides = map_slides_raw_to_canonical(raw.slidesTeamDeck)
    if not slides.slides:
        raise HTTPException(status_code=400, detail="slidesTeamDeck.slides is empty")

    slide_messages = generate_slide_messages(
        di_data=di_data,
        slides_data=slides,
        user_profile_raw=raw_profile
    )

    lecture_id = raw.lectureId or (raw.slidesTeamScript.lectureId if raw.slidesTeamScript and raw.slidesTeamScript.lectureId else f"lec-{uuid.uuid4()}")
    return VoiceTranscriptSlimResponse(
        lectureId=lecture_id,
        slideMessages=slide_messages,
        userProfile=raw_profile
    )

# =========================
# Optional: quick demo (python voice_transcript_generator.py)
# =========================

if __name__ == "__main__":
    # Minimal self-test (runs the LLM twice; may take time on first model download)
    demo_user = RawUserProfile(
        id="u123",
        role="student",
        language="english",
        preferences=RawUserPreferences(
            answerLength="medium",
            languageLevel="intermediate",
            expertiseLevel="beginner",
            includePictures="few"
        ),
        enrolledCourses=["SE001","cs001"]
    )

    demo_di = RawDIContent(
        content=[
            "In Python, a for loop is often used with the range() function to execute a block of code a specific number of times. For example: for i in range(5): print(i) will print numbers 0 through 4.",
            "A loop body runs once per item in the sequence; indentation defines the block to repeat."
        ]
    )

    demo_deck = RawSlidesDeck(
        title="Introduction to the For Loop",
        slides=[
            RawSlidesDeckSlide(
                title="What is a For Loop?",
                content="A for loop is a fundamental control flow statement for iteration. It repeats a block when you know the number of steps."
            ),
            RawSlidesDeckSlide(
                title="A Simple Example in Python",
                content="Using range(5), the loop runs five times. For example: for i in range(5): print('Hello!')."
            )
        ]
    )

    # Map + generate
    persona = map_user_profile_to_persona(demo_user)
    raw_profile = raw_profile_dict(demo_user)
    di_data = map_di_raw_to_canonical(demo_di)
    slides = map_slides_raw_to_canonical(demo_deck)

    msgs = generate_slide_messages(di_data=di_data, slides_data=slides, user_profile_raw=raw_profile)

    print("\n=== Demo Slim Output ===")
    print(_json.dumps({
        "lectureId": f"lec-{uuid.uuid4()}",
        "slideMessages": msgs,
        "userProfile": raw_profile
    }, indent=2))
    print("\nTip: run the API with:")
    print("  uvicorn voice_transcript_generator:app --reload --port 8082")
