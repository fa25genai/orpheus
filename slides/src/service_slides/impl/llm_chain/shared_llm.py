import os
import re
from typing import Optional, Any, TypeVar, Dict, cast

from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.language_models.base import BaseLanguageModel

# Provider-specific imports
from langchain_ollama.llms import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrockConverse

T = TypeVar("T")


def _remove_thinking_tags(text: str) -> str:
    """
    Removes <think>...</think> and <thinking>...</thinking> tags and their content from the text.
    
    Args:
        text: Input text that may contain thinking tags
        
    Returns:
        Text with all thinking tags and their content removed
    """
    if not text:
        return text
    
    # Remove <think>...</think> tags and their content
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Remove <thinking>...</thinking> tags and their content  
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    
    return text.strip()


def _create_llm_chain(
    model: BaseLanguageModel[Any],
    prompt: ChatPromptTemplate,
    parser: Optional[BaseOutputParser[Any]] = None,
) -> Runnable[Any, Any]:
    """Creates LLM chain from model, prompt and optional parser."""
    if parser is None:
        parser = StrOutputParser()

    return prompt | model | _remove_thinking_tags | parser


def invoke_llm(
    model: BaseLanguageModel[Any],
    prompt: ChatPromptTemplate,
    input_data: Dict[str, Any] = {},
    parser: Optional[BaseOutputParser[Any]] = None,
) -> Any:
    """Executes LLM request and returns parsed result."""
    chain = _create_llm_chain(model, prompt, parser)
    return cast(Any, chain.invoke(input_data))


def create_base_model(
    model_name: str, temperature: float = 0.0, max_tokens: Optional[int] = None
) -> BaseLanguageModel[Any]:
    """Creates the best available model based on environment variables."""

    # Try OpenAI first
    if "OPENAI_API_KEY" in os.environ:
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**model_kwargs)  # type: ignore

    # Try Google GenAI second
    if "GOOGLE_API_KEY" in os.environ:
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
        }
        if max_tokens:
            model_kwargs["max_output_tokens"] = max_tokens
        return ChatGoogleGenerativeAI(**model_kwargs)

    # Try Ollama third
    if "OLLAMA_LLM_HOST" in os.environ and "OLLAMA_LLM_KEY" in os.environ:
        model_kwargs = {
            "model": model_name,
            "base_url": os.environ["OLLAMA_LLM_HOST"],
            "temperature": temperature,
            "keep_alive": "-1m",
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        if "OLLAMA_LLM_KEY" in os.environ:
            model_kwargs["client_kwargs"] = {
                "headers": {"Authorization": f"Bearer {os.environ['OLLAMA_LLM_KEY']}"}
            }
        return OllamaLLM(**model_kwargs)  # type: ignore
    
    # Try AWS Bedrock last
    if "AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_ACCESS_KEY" in os.environ and "AWS_SESSION_TOKEN" in os.environ and "AWS_PROVIDER" in os.environ:
        model_kwargs = {
            "model_id": model_name,
            "temperature": temperature,
            "provider": os.environ["AWS_PROVIDER"]
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        return ChatBedrockConverse(**model_kwargs)  # type: ignore

    raise RuntimeError(
        "No LLM providers available. Please set one of: "
        "OPENAI_API_KEY, GOOGLE_API_KEY, OLLAMA_LLM_HOST, or AWS_ACCESS_KEY_ID with AWS_SECRET_ACCESS_KEY with AWS_SESSION_TOKEN"
        "in your environment variables."
    )
