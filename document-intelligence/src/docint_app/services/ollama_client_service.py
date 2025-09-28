import os
from typing import Optional

import ollama

_instance: Optional[ollama.Client] = None


def get_ollama_client(base_url: str = "https://gpu.aet.cit.tum.de/ollama") -> ollama.Client:
    """Singleton pattern to get Ollama client."""
    global _instance
    if _instance is None:
        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is required")

        _instance = ollama.Client(host=base_url.rstrip("/"), headers={"Authorization": f"Bearer {api_key}"})
    return _instance
