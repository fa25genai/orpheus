import ollama
import base64
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KEY", "")

# --- Client unverändert lassen ---
client = ollama.Client(
    host='https://gpu.aet.cit.tum.de/ollama',
    headers={'Authorization': f'Bearer {api_key}'}
)

def getImageCaption(base64_string, apikey=api_key):
    """
    Nimmt Base64 und gibt eine flache Caption zurück.
    """
    prompt = (
        "Explain the given image. Write the explanation into a single, continuous string. "
        "Do not include any formatting, markdown, or commentary. Provide ONLY the raw, extracted text."
    )

    try:
        image_bytes = base64.b64decode(base64_string)
    except Exception as e:
        print(f"Base64 decode error: {e}")
        return ""

    try:
        response = client.chat(
            model='gemma3:27b',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_bytes],
            }],
        )
        return (response.get('message', {}).get('content', "") or "").strip()
    except ollama.RequestError as e:
        print(f"Ollama error: {e.error}")
        if getattr(e, "status_code", None) == 401:
            print("Authentication failed. Check KEY.")
        return ""
    except Exception as e:
        print(f"Unexpected error: {e}")
        return ""

def caption_images_grouped(images_grouped, apikey=api_key):
    """
    Erwartet:
      List[List[{'data': <base64>}]]
    Druckt die Captions direkt und gibt die Daten zusätzlich zurück.
    """
    out = []
    for page_idx, page_items in enumerate(images_grouped, start=1):
        if not page_items:
            print(f"[Seite {page_idx}] (keine Bilder)")
            out.append([])
            continue

        page_out = []
        for img_idx, item in enumerate(page_items, start=1):
            caption = getImageCaption(item["data"], apikey)
            page_out.append({
                "data": item["data"],
                "caption": caption
            })
            # Direkt in der Funktion drucken
            cap = caption or "<leer oder blockiert>"
            print(f"[Seite {page_idx}, Bild {img_idx}] {cap}")
        out.append(page_out)

    total = sum(len(p) for p in out)
    print(f"Seiten: {len(out)} | Bilder: {total}")

    return out
