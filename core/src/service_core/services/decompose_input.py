"""
Simpler Python script: Question Refinement with Gemini/HuggingFace fallback

This script takes a student's free-form question and refines it into a set of
retrieval-friendly sub-queries and an answer plan using an LLM.

It will try HuggingFace first (if configured), but automatically fall back to
Gemini (via google-generativeai) if HuggingFace errors out.
"""

import json
import os
import textwrap
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# -----------------------------
# CONFIGURATION
# -----------------------------
class Config(BaseModel):
    llama_api_key: str = os.environ.get("LLAMA_API_KEY", "")
    llama_model: str = os.environ.get("LLAMA_MODEL", "")
    llama_api_url: str = os.environ.get("LLAMA_API_URL", "")

cfg = Config()


# -----------------------------
# Llama API helper
# -----------------------------
def call_llama(prompt: str, model: str = None, max_tokens: int = 512) -> str:
    """Call Llama API via LangChain ChatOllama"""
    model = model or cfg.llama_model
    if not cfg.llama_api_key:
        raise RuntimeError("LLAMA_API_KEY not set")
    
    # Initialize ChatOllama with custom endpoint and API key
    llm = ChatOllama(
        model=model,
        base_url=cfg.llama_api_url,
        headers={"Authorization": f"Bearer {cfg.llama_api_key}"},
    )
    
    # Generate response
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, 'content') else str(response).strip()

# -----------------------------
# Unified LLM caller
# -----------------------------
def llm_call(prompt: str) -> str:
    if cfg.llama_api_key:
        return call_llama(prompt)
    raise RuntimeError("No valid LLM API key available (Llama)")

# -----------------------------
# Question decomposition
# -----------------------------
DECOMPOSE_PROMPT = textwrap.dedent("""
You are an assistant that decomposes a student's question into concise,
retrieval-friendly sub-queries and a final answer plan.
Respond in strict JSON with keys: original_question, subqueries, answer_plan.

Rules:
- Keep subqueries short and focused.
- Do not add explanations outside JSON.
""")

def decompose_question(question: str) -> Dict[str, Any]:
    prompt = DECOMPOSE_PROMPT + "\n\n" + json.dumps({"original_question": question})
    raw = llm_call(prompt)
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
        raise RuntimeError("Failed to parse JSON from LLM output: " + raw)



