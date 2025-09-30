"""
Simpler Python script: Question Refinement with Gemini/HuggingFace fallback
...
"""

import json
import textwrap
from typing import Any, Dict, List
import logging
from pydantic import BaseModel

from dotenv import load_dotenv
# from langchain_community.chat_models import ChatOllama


from service_core.services.llm_chain.azure_llm import azure_with_string_output, azure_with_structured_output

logger = logging.getLogger("Decompose Input")

# Load environment variables from .env file
load_dotenv()

def llm_call(prompt: str) -> str:
    return azure_with_string_output(prompt)


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

class ExtractionModel(BaseModel):
    original_question: str
    subqueries: List[str]
    answer_plan: str

def decompose_question(question: str) -> Dict[str, Any]:
    """
    Decomposes a question into sub-queries and an answer plan using a structured output LLM call.

    Args:
        question: The user's question.

    Returns:
        A dictionary containing the original question, sub-queries, and an answer plan.
    """
    prompt = DECOMPOSE_PROMPT + "\n\nQuestion to analyze: " + json.dumps(question)

    try:
        structured_output: ExtractionModel = azure_with_structured_output(
            prompt, ExtractionModel
        )
        return structured_output.model_dump()
    except Exception as e:
        logger.error(f"Failed to get structured output from LLM: {e}")
        # Fallback or re-raising the exception might be needed depending on desired behavior
        raise RuntimeError(f"Failed to process question with structured output LLM: {e}")

