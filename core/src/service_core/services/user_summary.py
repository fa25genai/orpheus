import httpx
from service_core.services.helpers.llm import ask_llm
from service_core.impl.tracker import tracker


def summarize_content_with_llama(content: str) -> str:
    """Summarize the given content using Llama via llm_call, returning only the summary text."""
    prompt = f"Summarize the following content in 3-4 sentences. Only return the summary, do not preface with any explanation or heading.\n\n{content}"
    user_summary = ask_llm(prompt)
    tracker.log("Generated Summary:")
    tracker.log(user_summary)
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

