from typing import Any, Dict

import httpx

from service_core.services.helpers.llm import ask_llm


def extract_text_content(data: Dict[str, Any]) -> str:
    """Extract only the text content from a list of dicts, ignoring images or other fields."""

    if not isinstance(data, list):
        return str(data)

    texts = []
    for item in data:
        # Try common keys for text content
        if isinstance(item, dict):
            if "content" in item:
                texts.append(str(item["content"]))
    return "\n".join(texts) 


def summarize_content_with_llama(retrieved_content: Dict[str, Any]) -> str:
    """Summarize only the text content from retrieved_content using Llama via llm_call."""
    text_content = extract_text_content(retrieved_content)
    print("Text content to summarize:", text_content, flush=True)
    prompt = f"Summarize the following content in 3-4 sentences. Only return the summary, do not preface with any explanation or heading.\n\n{text_content}"
    user_summary: str = ask_llm(prompt)  
    print("Generated summary:", user_summary, flush=True)
    return user_summary


async def send_summary_to_endpoint(summary: str, client: httpx.AsyncClient) -> None:  
    summary_endpoint = "http://summary-receiver:9001/v1/summary"
    try:
        response = await client.post(
            summary_endpoint,
            json={"summary": summary},
            timeout=60.0,
        )
        response.raise_for_status()
        print("Summary sent successfully", flush=True)
    except Exception as e:
        print("Error sending summary to endpoint:", e, flush=True)


async def summarize_and_send(content: Dict[str, Any], client: httpx.AsyncClient) -> None:
    summary = summarize_content_with_llama(content)
    await send_summary_to_endpoint(summary, client)
