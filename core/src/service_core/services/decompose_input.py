"""
Simpler Python script: Question Refinement with Gemini/HuggingFace fallback
...
"""

import json
import os
import textwrap
from typing import Any, Dict, Optional
import logging

from dotenv import load_dotenv
# from langchain_community.chat_models import ChatOllama


from service_core.services.llm_chain.shared_llm import create_base_model

logger = logging.getLogger("Decompose Input")

# Load environment variables from .env file
load_dotenv()


# -----------------------------
# Llama API helper
# -----------------------------
def call_llm(prompt: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
    model_name = os.getenv("MODEL_NAME")
    if model_name is None:
        raise ValueError("MODEL_NAME environment variable is not set")

    logger.info(f"Initializing model: {model_name}")
    llm = create_base_model(model_name, temperature=0.0)

    # Generate response
    response = llm.invoke(prompt)
    text = getattr(response, "content", response)
    return str(text).strip()


def llm_call(prompt: str) -> str:
    return call_llm(prompt)


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


def extract_json_from_markdown(question: str) -> str:
    prompt = DECOMPOSE_PROMPT + "\n\nQuestion to analyze: " + json.dumps(question)
    raw_llm_output = llm_call(prompt)  # e.g. still including markdown

    # Clean the response - remove any potential Markdown formatting
    raw_llm_output = raw_llm_output.strip()
    if raw_llm_output.startswith("```json"):
        raw_llm_output = raw_llm_output[7:]
    if raw_llm_output.startswith("```"):
        raw_llm_output = raw_llm_output[3:]
    if raw_llm_output.endswith("```"):
        raw_llm_output = raw_llm_output[:-3]
    raw_llm_output = raw_llm_output.strip()

    return raw_llm_output


def decompose_question(question: str) -> Dict[str, Any]:
    raw_llm_output: str = extract_json_from_markdown(question)

    try:
        questions_generated_from_user_query: Dict[str, Any] = json.loads(raw_llm_output)
        # Validate required keys
        required_keys = ["original_question", "subqueries"]
        if not all(key in questions_generated_from_user_query for key in required_keys):
            raise ValueError(
                f"Missing required keys. Expected: {required_keys}, Got: {list(questions_generated_from_user_query.keys())}"
            )

        # Ensure subqueries is a list
        if not isinstance(questions_generated_from_user_query["subqueries"], list):
            raise ValueError("subqueries must be an array")

        return questions_generated_from_user_query
    except json.JSONDecodeError as e:
        # TODO extract to a method
        # if we do not find the expected keys in the initial datastructure,
        # we try to clean up the format and search again for the keys (e.g. there could be a space before the brackets, things like that)
        # Try to extract JSON from the response
        start, end = raw_llm_output.find("{"), raw_llm_output.rfind("}")
        if start != -1 and end != -1:
            try:
                questions_generated_from_user_query = json.loads(
                    raw_llm_output[start : end + 1]
                )
                # Validate required keys for extracted JSON too
                required_keys = ["original_question", "subqueries"]
                if not all(
                    key in questions_generated_from_user_query for key in required_keys
                ):
                    raise ValueError(
                        f"Missing required keys in extracted JSON. Expected: {required_keys}, Got: {list(questions_generated_from_user_query.keys())}"
                    )
                return questions_generated_from_user_query
            except json.JSONDecodeError:
                pass
        raise RuntimeError(
            f"Failed to parse JSON from LLM output. JSON Error: {e}. Raw output: {raw_llm_output[:200]}..."
        )
