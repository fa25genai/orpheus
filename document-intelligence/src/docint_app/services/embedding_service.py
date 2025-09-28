"""
Embedding Service using Ollama API
"""

from typing import List, Optional

from docint_app.services.ollama_client_service import get_ollama_client


class EmbeddingService:

    def __init__(self):
        self.client = get_ollama_client()
        self.model = "nomic-embed-text:latest"

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a single text using Ollama API.

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector
        """
        print("Generating embedding for text...")
        
        response = self.client.embeddings(model=self.model, prompt=text)
        print(f"Received embedding of dimension {len(response['embedding'])}")
        print(f"Response: {response}")
        return response["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings

_instance: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _instance
    if _instance is None:
        _instance = EmbeddingService()
    return _instance
