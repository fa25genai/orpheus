from typing import List

from service_core.models.docint.retrieval_response import RetrievalResponse
from service_core.services.helpers.llm import ask_llm


def extract_text_content(data: List[RetrievalResponse]) -> str:
    """Extract only the text content from a list of dicts, ignoring images or other fields."""

    if not isinstance(data, list):
        return str(data)

    texts = []
    for item in data:
        texts.append(str(item))
    return "\n".join(texts)


def summarize_content_with_llama(
    retrieved_content: List[RetrievalResponse], user_prompt: str
) -> str:
    """Summarize only the text content from retrieved_content using Llama via llm_call."""
    text_content = extract_text_content(retrieved_content)
    # print("Text content to summarize:", text_content, flush=True)
    prompt = f'Summarize the following content in 3-4 sentences. Only return the summary with respect to user query, do not preface with any explanation or heading and return "Query irrelevant to course content" if it\'s unrelated.\n\n{text_content}\n\nUser prompt: {user_prompt}'
    user_summary: str = ask_llm(prompt)
    # print("Generated summary:", user_summary, flush=True)
    return user_summary
