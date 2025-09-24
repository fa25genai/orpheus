import os
from typing import Optional, Any, TypeVar, Dict

from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.language_models.base import BaseLanguageModel

# Provider-specific imports
from langchain_ollama.llms import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

T = TypeVar("T")


def _create_llm_chain(
    model: BaseLanguageModel,
    prompt: ChatPromptTemplate,
    parser: Optional[BaseOutputParser[T]] = None,
) -> Runnable:
    """Creates LLM chain from model, prompt and optional parser."""
    if parser is None:
        parser = StrOutputParser()

    return prompt | model | parser


def invoke_llm(
    model: BaseLanguageModel,
    prompt: ChatPromptTemplate,
    input_data: Dict[str, Any] = {},
    parser: Optional[BaseOutputParser[T]] = None,
) -> T | str:
    """Executes LLM request and returns parsed result."""
    chain = _create_llm_chain(model, prompt, parser)
    return chain.invoke(input_data)


def create_base_model(
    model_name: str, temperature: float = 0.0, max_tokens: Optional[int] = None
) -> BaseLanguageModel:
    """Creates the best available model based on environment variables."""

    # Try OpenAI first
    if "OPENAI_API_KEY" in os.environ:
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**model_kwargs)

    # Try Google GenAI second
    if "GOOGLE_API_KEY" in os.environ:
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
        }
        if max_tokens:
            model_kwargs["max_output_tokens"] = max_tokens
        return ChatGoogleGenerativeAI(**model_kwargs)

    # Try Ollama last
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
        return OllamaLLM(**model_kwargs)

    raise RuntimeError(
        "No LLM providers available. Please set one of: "
        "OPENAI_API_KEY, GOOGLE_API_KEY, or OLLAMA_LLM_HOST "
        "in your environment variables."
    )
