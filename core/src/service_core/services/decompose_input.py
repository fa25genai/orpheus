"""
Simpler Python script: Question Refinement with Gemini/HuggingFace fallback
...
"""

import json
import os
import textwrap
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
# from langchain_community.chat_models import ChatOllama
from langchain_community.chat_models import BedrockChat

from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


# -----------------------------
# CONFIGURATION
# -----------------------------
class Config(BaseModel):
    aws_access_key_id: str | None = os.environ.get("AWS_ACCESS_KEY_ID", None)
    aws_secret_access_key: str | None = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
    aws_session_token: str | None = os.environ.get("AWS_SESSION_TOKEN", None)

    llama_api_key: str | None = os.environ.get("LLAMA_API_KEY", None)
    llama_model: str | None = os.environ.get("LLAMA_MODEL", None)
    llama_api_url: str | None = os.environ.get("LLAMA_API_URL", None)

    access_key = aws_access_key_id if aws_access_key_id is not None else None
    secret_access_key = aws_secret_access_key if aws_secret_access_key is not None else None
    session_token = aws_session_token if aws_session_token is not None else None

config = Config()


# -----------------------------
# Llama API helper
# -----------------------------
def call_llama(prompt: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
    """Call Llama API via LangChain ChatOllama"""
    model = model or config.llama_model
    if not config.llama_api_key:
        raise RuntimeError("LLAMA_API_KEY not set")

    # Initialize ChatOllama with custom endpoint and API key
    # llm = ChatOllama(
    #     model=model,
    #     base_url=config.llama_api_url,
    #     headers={"Authorization": f"Bearer {config.llama_api_key}"},
    # )

    # https://eu-central-1.console.aws.amazon.com/bedrock/home?region=eu-central-1#/model-catalog
    llm = ChatBedrockConverse(
        model="amazon.nova-micro-v1:0",  # or another supported model
        region_name="eu-central-1",         # set your AWS region
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
        aws_session_token=config.aws_session_token,
    )

    # Generate response
    response = llm.invoke(prompt)
    text = getattr(response, "content", response)
    return str(text).strip()


def llm_call(prompt: str) -> str:
    if config.llama_api_key:
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

def extract_json_from_markdown(question: str) -> str:
    prompt = DECOMPOSE_PROMPT + "\n\nQuestion to analyze: " + json.dumps(question)
    raw_llm_output = llm_call(prompt) # e.g. still including markdown

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
            raise ValueError(f"Missing required keys. Expected: {required_keys}, Got: {list(questions_generated_from_user_query.keys())}")

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
                questions_generated_from_user_query = json.loads(raw_llm_output[start: end + 1])
                # Validate required keys for extracted JSON too
                required_keys = ["original_question", "subqueries"]
                if not all(key in questions_generated_from_user_query for key in required_keys):
                    raise ValueError(f"Missing required keys in extracted JSON. Expected: {required_keys}, Got: {list(questions_generated_from_user_query.keys())}")
                return questions_generated_from_user_query
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Failed to parse JSON from LLM output. JSON Error: {e}. Raw output: {raw_llm_output[:200]}...")
