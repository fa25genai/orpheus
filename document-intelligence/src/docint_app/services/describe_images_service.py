"""
Image Description Service using Ollama API
"""

import os
import base64
from typing import List, Dict, Any, Optional

import ollama


class ImageDescriptionService:
    def __init__(self, base_url: str = "https://gpu.aet.cit.tum.de/ollama"):
        self.base_url = base_url.rstrip("/")
        self.model = "gemma3:27b"
        self._client = None
    
    @property
    def client(self) -> ollama.Client:
        """Lazy initialization of Ollama client."""
        if self._client is None:
            api_key = os.getenv("OLLAMA_API_KEY")
            if not api_key:
                raise ValueError("OLLAMA_API_KEY environment variable is required")

            self._client = ollama.Client(
                host=self.base_url,
                headers={'Authorization': f'Bearer {api_key}'}
            )
        return self._client
    
    def _get_image_caption(self, base64_string: str) -> str:
        """
        Generate a caption for a single image from base64 string.
        
        Args:
            base64_string: Base64 encoded image data
            
        Returns:
            Image caption as string
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
            response = self.client.chat(
                model=self.model,
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
                print("Authentication failed. Check OLLAMA_API_KEY.")
            return ""
        except Exception as e:
            print(f"Unexpected error: {e}")
            return ""
    
    def caption_images_grouped(self, images_grouped: List[List[Dict[str, str]]]) -> List[List[Dict[str, str]]]:
        """
        Generate captions for grouped images (by pages).
        
        Args:
            images_grouped: List of pages, each containing list of images with 'data' key
            
        Returns:
            List of pages with images containing both 'data' and 'caption' keys
        """
        out = []
        for page_idx, page_items in enumerate(images_grouped, start=1):
            if not page_items:
                print(f"[Seite {page_idx}] (keine Bilder)")
                out.append([])
                continue

            page_out = []
            for img_idx, item in enumerate(page_items, start=1):
                caption = self._get_image_caption(item["data"])
                page_out.append({
                    "data": item["data"],
                    "caption": caption
                })
                # Print caption directly
                cap = caption or "<leer oder blockiert>"
                print(f"[Seite {page_idx}, Bild {img_idx}] {cap}")
            out.append(page_out)

        total = sum(len(p) for p in out)
        print(f"Seiten: {len(out)} | Bilder: {total}")

        return out


def get_image_description_service() -> ImageDescriptionService:
    """Factory function to get ImageDescriptionService instance."""
    return ImageDescriptionService()
