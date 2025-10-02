"""
PDF Image Extraction Service using PyMuPDF
"""

import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF
from PIL import Image, ImageStat


class PDFImageExtractorService:
    """Service for extracting images from PDF documents."""

    def __init__(self, darkness_threshold: int = 30, variance_threshold: int = 15):
        """
        Initialize the PDF image extractor service.
        Args:
            darkness_threshold: Threshold for detecting dark images
            variance_threshold: Threshold for detecting low-variance images
        """
        self.darkness_threshold = darkness_threshold
        self.variance_threshold = variance_threshold

    def _is_black_square(self, img_bytes: bytes) -> bool:
        """
        Heuristic for detecting black squares (e.g., code block placeholders).
        Args:
            img_bytes: Raw image bytes
        Returns:
            True if image appears to be a black square
        """
        try:
            image = Image.open(BytesIO(img_bytes)).convert("L")
            stat = ImageStat.Stat(image)
            return bool(stat.mean[0] < self.darkness_threshold and stat.stddev[0] < self.variance_threshold)
        except Exception as e:
            print(f"Error checking if image is black square: {e}")
            return False

    def extract_images_grouped(self, pdf_path: str) -> List[List[Dict[str, str]]]:
        """
        Extract images from PDF grouped by pages.
        Args:
            pdf_path: Path to the PDF file
        Returns:
            List of pages, each containing list of images with 'data' key
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF cannot be opened or processed
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        try:
            pdf = fitz.open(pdf_path)
        except Exception as e:
            raise Exception(f"Failed to open PDF: {e}")
        result = []
        print(f"Opening PDF: {pdf_path} | Pages: {len(pdf)}")
        try:
            for page_number, page in enumerate(pdf, start=1):
                print(f"\n[Page {page_number}] processing started...")
                page_items = []
                images = page.get_images(full=True)
                print(f"  Found images: {len(images)}")
                for img_index, (xref, smask, *_) in enumerate(images, start=1):
                    if smask:  # Skip soft masks
                        print(f"    [Image {img_index}] soft-mask recognized → skipped")
                        continue
                    try:
                        info = pdf.extract_image(xref)
                        img_bytes = info["image"]
                        if self._is_black_square(img_bytes):
                            print(f"    [Image {img_index}] black box detected → skipped")
                            continue
                        print(f"    [Image {img_index}] extracted (Size: {len(img_bytes)} bytes)")
                        page_items.append({"data": f"data:image/{info['ext']};base64,{base64.b64encode(img_bytes).decode('utf-8')}"})
                    except Exception as e:
                        print(f"    [Image {img_index}] error during extraction: {e}")
                        continue
                if not page_items:
                    print(f"  No valid images on page {page_number}")
                result.append(page_items)
        finally:
            pdf.close()
        total_images = sum(len(p) for p in result)
        print(f"\nExtraction done. Pages: {len(result)} | Images overall: {total_images}")
        return result


_instance: Optional[PDFImageExtractorService] = None


def get_pdf_image_extractor_service() -> PDFImageExtractorService:
    global _instance
    if _instance is None:
        _instance = PDFImageExtractorService()
    return _instance
