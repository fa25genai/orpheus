import httpx
from typing import Dict, Any # FIX: [name-defined]
from service_core.services.helpers.llm import ask_llm
from service_core.impl.tracker import tracker


def extract_text_content(data: Dict[str, Any]) -> str: # FIX: [no-untyped-def] and [name-defined]
    """Extract only the text content from a list of dicts, ignoring images or other fields."""
    
    # FIX: [name-defined] - Replaced undefined `retrieved_content` with parameter `data`
    if not isinstance(data, list): 
        return str(data)
    
    texts = []
    # FIX: [name-defined] - Replaced undefined `retrieved_content` with parameter `data`
    for item in data:
        # Try common keys for text content
        if isinstance(item, dict):
            if "content" in item:
                texts.append(str(item["content"]))
    return "\n".join(texts) # FIX: [no-any-return]


def summarize_content_with_llama(retrieved_content: Dict[str, Any]) -> str: # FIX: [no-untyped-def]
    # print("Retrieved content for summarization:", retrieved_content, flush=True)
    """Summarize only the text content from retrieved_content using Llama via llm_call."""
    # FIX: [no-untyped-call] - Assuming `extract_text_content` is now typed
    text_content = extract_text_content(retrieved_content)
    print("Text content to summarize:", text_content, flush=True)
    prompt = f"Summarize the following content in 3-4 sentences. Only return the summary, do not preface with any explanation or heading.\n\n{text_content}"
    user_summary: str = ask_llm(prompt) # FIX: [no-any-return] and assuming `ask_llm` is typed to return str
    print("Generated summary:", user_summary, flush=True)
    return user_summary


async def send_summary_to_endpoint(summary: str, client: httpx.AsyncClient) -> None: # FIX: [no-untyped-def]
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
    # FIX: [name-defined] - Replaced undefined `retrieved_content` with parameter `content`
    summary = summarize_content_with_llama(content) 
    await send_summary_to_endpoint(summary, client)