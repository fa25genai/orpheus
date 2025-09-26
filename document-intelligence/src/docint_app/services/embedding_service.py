"""
Embedding Service using Ollama API
"""

import os
from typing import List

import httpx


class EmbeddingService:
    def __init__(self, base_url: str = "https://gpu.aet.cit.tum.de/ollama"):
        self.base_url = base_url.rstrip("/")
        self.model = "nomic-embed-text:latest"

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a single text using Ollama API.

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector
        """
        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is required")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/embeddings", json={"model": self.model, "prompt": text}, headers=headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            return result["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
