"""
Extract Text Service using Ollama API
"""

import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Optional

import ollama
from pdf2image import convert_from_path
from PIL import Image

from docint_app.services.ollama_client_service import get_ollama_client


class ExtractTextService:
    def __init__(self, base_url: str = "https://gpu.aet.cit.tum.de/ollama"):
        self.base_url = base_url.rstrip("/")
        self.model = "gemma3:27b"
        self.client = get_ollama_client()

    def extract_text_from_slide(self, image: Image.Image) -> str:
        """
        Extracts all text and formulas from a single slide image using Ollama API.
        Returns the raw extracted text as a string.
        """
        print("Extracting text from slide image...")
        byte_arr = io.BytesIO()
        image.save(byte_arr, format="PNG")
        print("Converted image to byte array.")
        image_bytes = byte_arr.getvalue()
        try:
            print("Sending image to Ollama for text extraction...")
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": ("Given the image of a single slide, extract all text and formulas. Consolidate the extracted content into a single, continuous string. Do not include any formatting, markdown, or commentary. Provide ONLY the raw, extracted text."),
                        "images": [image_bytes],
                    },
                ],
            )
            print("Received response from Ollama.")
            return str(response.get("message", {}).get("content", ""))
        except ollama.RequestError as e:
            print(f"Error: {getattr(e, 'error', e)}")
            status_code = getattr(e, "status_code", None)
            if status_code == 401:
                print("Authentication failed. Please check your API key.")
            else:
                print(f"An error occurred with status code {status_code}.")
        return ""

    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Converts a PDF to images and extracts text from each slide.
        Returns a list of extracted text blocks (one per page).
        """
        try:
            os.makedirs("tmp/rawimages/", exist_ok=True)
            pages = convert_from_path(pdf_path, 200, output_folder="tmp/rawimages/")
            for num, page in enumerate(pages, start=1):
                print(f"Page {page}")
            print("successfully converted images")
        except Exception as e:
            print("Error converting PDF to images. Ensure Poppler is installed and the path is correct.")
            print(f"Details: {e}")
            return []

        # Parallelize text extraction from pages
        def extract_from_page(page_data: tuple[int, Any]) -> tuple[int, str]:
            i, page = page_data
            print(f"Processing page {i + 1}")
            extracted_text = self.extract_text_from_slide(page)
            return i, extracted_text + "\n\n"

        texts = [""] * len(pages)  # Pre-allocate list to maintain order

        with ThreadPoolExecutor(max_workers=16) as executor:
            # Submit all tasks
            future_to_page = {executor.submit(extract_from_page, (i, page)): i for i, page in enumerate(pages)}

            # Collect results as they complete
            for future in as_completed(future_to_page):
                try:
                    page_index, slide_text_block = future.result()
                    texts[page_index] = slide_text_block
                    print(f"Completed page {page_index + 1}")
                except Exception as e:
                    page_index = future_to_page[future]
                    print(f"Error processing page {page_index + 1}: {e}")
                    texts[page_index] = ""

        print(f"Extracted text from {len(texts)} slides.")
        return texts

    @staticmethod
    def save_texts_to_txt(texts: List[str], base_filename: str = "output.txt") -> None:
        """
        Saves a list of text blocks to a file, incrementing a counter in the name if the file exists.
        """
        content = "".join(texts)
        name, ext = os.path.splitext(base_filename)
        filename = base_filename
        counter = 1
        while os.path.exists(filename):
            filename = f"{name}_{counter}{ext}"
            counter += 1
        try:
            with open(filename, "w") as file:
                file.write(content)
        except IOError as e:
            print(f"An error occurred while writing to the file: {e}")


_instance: Optional[ExtractTextService] = None


def get_extract_text_service() -> ExtractTextService:
    global _instance
    if _instance is None:
        _instance = ExtractTextService()
    return _instance
