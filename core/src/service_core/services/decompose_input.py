"""
Simpler Python script: Question Refinement with Gemini/HuggingFace fallback
...
"""

import json
import os
import textwrap
from typing import Any, Dict, Optional
from service_core.services.helpers.llm import ask_llm_with_model
from pydantic import BaseModel

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

class QueryModel(BaseModel):
    original_question: str
    subqueries: list[str]
    answer_plan: Optional[str] = None

def decompose_question(question: str) -> Dict[str, Any]:
    prompt = DECOMPOSE_PROMPT + "\n\nQuestion to analyze: " + json.dumps(question)
    output = ask_llm_with_model(prompt, QueryModel).model_dump_json()
    output = json.loads(output)
    return output