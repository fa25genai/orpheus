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
# JSON helpers
# -----------------------------
def try_parse_json(raw_response: str) -> tuple[bool, dict]:
    """Try to parse JSON response, return (success, result)"""
    try:
        result = json.loads(raw_response)
        return True, result
    except json.JSONDecodeError:
        return False, None


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
- Respond in strict JSON format with properly escaped strings:

{
  "lectureScript": "Your complete lecture script here as a single string with no line breaks",
  "Images": [{"image": "filename.jpg", "description": "Description text"}]
}

IMPORTANT: 
- The JSON must be valid and parseable
- Do NOT include actual line breaks in the lectureScript string value
- Use \\n for line breaks within the text if needed
- Start the lectureScript content immediately after the opening quote
- Do NOT produce slides or voice scripts at this stage
""")

def generate_script(retrieved_content: List[Dict[str, Any]], persona: Dict[str, Any]) -> Dict[str, Any]:
    if hasattr(persona, 'dict'):
        persona_dict = persona.dict()
    elif hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona

    persona_dict['id'] = str(persona_dict['id'])
    print("Refining lecture content for persona:")

    prompt = REFINE_PROMPT + "\n\n" + json.dumps({
        "persona": persona_dict,
        "retrieved_content": retrieved_content
    }, ensure_ascii=False)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            raw = llm_call(prompt)       
            print(f"\nBreak point (attempt {attempt + 1}): {raw}")
            
            # Try to parse JSON directly first
            success, result = try_parse_json(raw)
            if success:
                return result
            
            # If it didn't work, this will raise JSONDecodeError and trigger retry
            json.loads(raw)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error on attempt {attempt + 1}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to get valid response from LLM after {max_retries} attempts: {e}")
            continue

