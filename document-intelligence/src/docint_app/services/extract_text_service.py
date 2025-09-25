

"""
Extract Text Service using Ollama API
"""

import os
import io
from typing import List
from PIL import Image
from pdf2image import convert_from_path
import ollama
from dotenv import load_dotenv


class ExtractTextService:
    def __init__(self, base_url: str = "https://gpu.aet.cit.tum.de/ollama"):
        load_dotenv()
        self.base_url = base_url.rstrip("/")
        self.api_key = os.getenv("OLLAMA_API_KEY")
        if not self.api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is required")
        self.model = "gemma3:27b"
        self.client = ollama.Client(
            host=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    def extract_text_from_slide(self, image: Image.Image) -> str:
        """
        Extracts all text and formulas from a single slide image using Ollama API.
        Returns the raw extracted text as a string.
        """
        byte_arr = io.BytesIO()
        image.save(byte_arr, format='PNG')
        image_bytes = byte_arr.getvalue()
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': (
                            "Given the image of a single slide, extract all text and formulas. "
                            "Consolidate the extracted content into a single, continuous string. "
                            "Do not include any formatting, markdown, or commentary. "
                            "Provide ONLY the raw, extracted text."
                        ),
                        'images': [image_bytes]
                    },
                ],
            )
            return response['message']['content']
        except ollama.RequestError as e:
            print(f"Error: {e.error}")
            if e.status_code == 401:
                print("Authentication failed. Please check your API key.")
            else:
                print(f"An error occurred with status code {e.status_code}.")
        return ""

    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Converts a PDF to images and extracts text from each slide.
        Returns a list of extracted text blocks (one per page).
        """
        try:
            pages = convert_from_path(pdf_path, 200)
            print("successfully converted images")
        except Exception as e:
            print("Error converting PDF to images. Ensure Poppler is installed and the path is correct.")
            print(f"Details: {e}")
            return []
        texts = []
        for i, page in enumerate(pages):
            slide_text_block = ""
            extracted_text = self.extract_text_from_slide(page)
            slide_text_block += extracted_text + '\n\n'
            texts.append(slide_text_block)
        self.save_texts_to_txt(texts, "lectureSlides/out.txt")
        return texts

    @staticmethod
    def save_texts_to_txt(texts: List[str], base_filename: str = "output.txt"):
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
            with open(filename, 'w') as file:
                file.write(content)
        except IOError as e:
            print(f"An error occurred while writing to the file: {e}")


def get_extract_text_service() -> ExtractTextService:
    return ExtractTextService()