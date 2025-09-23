"""
Python script: Refine lecture content based on student persona

This script takes:
1. Retrieved content from RAG for sub-questions
2. A student's persona

It produces a single lecture script with image references.
Output format:
{
  "lectureScript": "...",
  "Images": [{"image": "...", "description": "..."}]
}
"""

import os
import json
import textwrap
from typing import Dict, Any, List
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama

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
def call_llama(prompt: str, model: str = None, max_tokens: int = 1024) -> str:
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
# Refine lecture content
# -----------------------------
REFINE_PROMPT = textwrap.dedent("""
You are an assistant that produces a coherent answer to a question based on the provided content and student persona.

Inputs:
- A student persona (id, role, language, preferences, enrolled cources).
- A list of retrieved content (text + images) for a lecture.                               

Task:
- Combine the retrieved content into a single lecture script.
- Adapt the content difficulty and explanation based on the student's persona.
- Make the script formal.
- Reference images inline where appropriate (e.g., "see image: <description>").
- Respond in strict JSON format:

{
  "lectureScript": "...",
  "Images": [{"image": "...", "description": "..."}]
}

Do NOT produce slides or voice scripts at this stage.
""")

def refine_lecture_content(retrieved_content: List[Dict[str, Any]], persona: Dict[str, Any]) -> Dict[str, Any]:
    if hasattr(persona, 'dict'):
        persona_dict = persona.dict()
    elif hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona
        
    persona_dict['id'] = str(persona_dict['id'])
    
    prompt = REFINE_PROMPT + "\n\n" + json.dumps({
        "persona": persona_dict,
        "retrieved_content": retrieved_content
    }, ensure_ascii=False)
    raw = llm_call(prompt)
    try:
        return json.loads(raw)
    except Exception:
        # Fallback: try extracting JSON substring
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
        raise RuntimeError("Failed to parse JSON from LLM output: " + raw)

