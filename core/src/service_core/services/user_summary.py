import httpx
from service_core.services.helpers.llm import ask_llm
from service_core.impl.tracker import tracker


def extract_text_content(retrieved_content):
    """Extract only the text content from a list of dicts, ignoring images or other fields."""
    if not isinstance(retrieved_content, list):
        return str(retrieved_content)
    texts = []
    for item in retrieved_content:
        # Try common keys for text content
        if isinstance(item, dict):
            if "content" in item:
                texts.append(str(item["content"]))
    return "\n".join(texts)


def summarize_content_with_llama(retrieved_content) -> str:
    # print("Retrieved content for summarization:", retrieved_content, flush=True)
    """Summarize only the text content from retrieved_content using Llama via llm_call."""
    text_content = extract_text_content(retrieved_content)
    print("Text content to summarize:", text_content, flush=True)
    prompt = f"Summarize the following content in 3-4 sentences. Only return the summary, do not preface with any explanation or heading.\n\n{text_content}"
    user_summary = ask_llm(prompt)
    print("Generated summary:", user_summary, flush=True)
    return user_summary


async def send_summary_to_endpoint(summary, client):
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


async def summarize_and_send(retrieved_content, client):
    summary = summarize_content_with_llama(retrieved_content)
    # await send_summary_to_endpoint(summary, client)
