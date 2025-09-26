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
from typing import Any, Dict, Optional, cast

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
def call_llama(prompt: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
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
    text = getattr(response, "content", response)
    return str(text).strip()


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
You are an assistant that intelligently analyzes a student's question and decomposes it only when necessary.

CRITICAL: You MUST output ONLY valid JSON with no additional text, comments, or explanations.

Required JSON structure:
{
  "original_question": "the exact input question",
  "subqueries": ["array of sub-questions"],
}

Analysis Rules:
1. If the question is already simple, focused, and clear (1-2 concepts), return it as a single subquery
2. Only decompose if the question contains multiple distinct concepts or requirements
4. Each subquery should be self-contained and retrieval-optimized
5. Preserve all user requirements and context from the original question
6. Don't create artificial complexity - simple questions deserve simple treatment

JSON Requirements:
- Output ONLY the JSON object
- No markdown formatting, no code blocks, no explanations
- Ensure all strings are properly escaped
- All keys must be present
- subqueries must be an array (even if single item)
""")


def decompose_question(question: str) -> Dict[str, Any]:
    prompt = DECOMPOSE_PROMPT + "\n\nQuestion to analyze: " + json.dumps(question)
    raw = llm_call(prompt)

    # Clean the response - remove any potential markdown formatting
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        result = json.loads(raw)
        # Validate required keys
        required_keys = ["original_question", "subqueries"]
        if not all(key in result for key in required_keys):
            raise ValueError(f"Missing required keys. Expected: {required_keys}, Got: {list(result.keys())}")

        # Ensure subqueries is a list
        if not isinstance(result["subqueries"], list):
            raise ValueError("subqueries must be an array")

        return result
    except json.JSONDecodeError as e:
        # Try to extract JSON from the response
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            try:
                result = json.loads(raw[start : end + 1])
                # Validate required keys for extracted JSON too
                required_keys = ["original_question", "subqueries"]
                if not all(key in result for key in required_keys):
                    raise ValueError(f"Missing required keys in extracted JSON. Expected: {required_keys}, Got: {list(result.keys())}")
                return result
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Failed to parse JSON from LLM output. JSON Error: {e}. Raw output: {raw[:200]}...")
