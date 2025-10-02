import os
from typing import Any, Dict, Optional, TypeVar, cast

from langchain_aws import ChatBedrockConverse
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

# Provider-specific imports
from langchain_ollama.llms import OllamaLLM
from langchain_openai import AzureChatOpenAI, ChatOpenAI

T = TypeVar("T")


def _create_llm_chain(
    model: BaseLanguageModel[Any],
    prompt: ChatPromptTemplate,
    parser: Optional[BaseOutputParser[Any]] = None,
) -> Runnable[Any, Any]:
    """Creates LLM chain from model, prompt and optional parser."""
    if parser is None:
        parser = StrOutputParser()

    return prompt | model | parser


def invoke_llm(
    model: BaseLanguageModel[Any],
    prompt: ChatPromptTemplate,
    input_data: Dict[str, Any] = {},
    parser: Optional[BaseOutputParser[Any]] = None,
) -> Any:
    """Executes LLM request and returns parsed result."""
    chain = _create_llm_chain(model, prompt, parser)
    return cast(Any, chain.invoke(input_data))


def create_base_model(model_name: str, temperature: float = 0.0, max_tokens: Optional[int] = None) -> BaseLanguageModel[Any]:
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
    if "OLLAMA_LLM_HOST" in os.environ:
        model_kwargs = {
            "model": model_name,
            "base_url": os.environ["OLLAMA_LLM_HOST"],
            "temperature": temperature,
            "keep_alive": "-1m",
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        if "OLLAMA_LLM_KEY" in os.environ:
            model_kwargs["client_kwargs"] = {"headers": {"Authorization": f"Bearer {os.environ['OLLAMA_LLM_KEY']}"}}
        return OllamaLLM(**model_kwargs)  # type: ignore

    # Try AWS Bedrock fourth
    if "AWS_BEARER_TOKEN_BEDROCK" in os.environ:
        model_kwargs = {
            "model_id": model_name,
            "temperature": temperature,
            "provider": os.environ["AWS_PROVIDER"],
        }
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        return ChatBedrockConverse(**model_kwargs)  # type: ignore

    # Try Azure OpenAI last
    if "AZURE_OPENAI_API_KEY" in os.environ and "AZURE_OPENAI_API_BASE" in os.environ and "AZURE_OPENAI_API_VERSION" in os.environ:
        return AzureChatOpenAI(
            azure_deployment= model_name,
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=os.environ["AZURE_OPENAI_API_BASE"],
            reasoning_effort="low",
            max_tokens=max_tokens,
        )

    raise RuntimeError("No LLM providers available. Please set open ai, google, ollama, aws, or azure configurations in your environment variables.")
