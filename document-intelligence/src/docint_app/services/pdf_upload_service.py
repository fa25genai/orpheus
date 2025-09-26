"""
PDF Upload Service
Processes PDF files by extracting text and images, generating descriptions, and storing in vector database.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union

from docint_app.services.describe_images_service import get_image_description_service
from docint_app.services.extract_text_service import get_extract_text_service
from docint_app.services.ingestion_service import IngestionService
from docint_app.services.pdf_image_extractor_service import get_pdf_image_extractor_service

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PDFUploadService:
    def __init__(self, base_url: str = "http://docint-weaviate:28947", storage_dir: str = "uploaded_pdfs"):
        """
        Initialize the PDF upload service with all required components.

        Args:
            base_url: Weaviate database URL
            storage_dir: Directory to store uploaded PDFs
        """

        base_url = os.getenv("WEAVIATE_URL", base_url)
        logger.info(f"Initializing PDFUploadService with base_url: {base_url}")
        try:
            self.text_extractor = get_extract_text_service()
            self.image_extractor = get_pdf_image_extractor_service()
            self.image_descriptor = get_image_description_service()
            self.ingestion_service = IngestionService(base_url=base_url)
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(exist_ok=True)
            logger.info("Successfully initialized all PDF processing services")
        except Exception as e:
            logger.error(f"Failed to initialize PDFUploadService: {e}")
            raise

    def _save_pdf(self, course_id: str, pdf_bytes: bytes) -> Tuple[str, str]:
        """
        Save PDF to storage with course name and timestamp.

        Args:
            course_id: Course identifier
            pdf_bytes: PDF file bytes

        Returns:
            Tuple of (saved_file_path, document_id)
        """
        # Create timestamp for unique file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create course directory
        course_dir = self.storage_dir / course_id
        course_dir.mkdir(exist_ok=True)

        # Generate document ID and filename
        document_id = f"{course_id}_{timestamp}"
        filename = f"{document_id}.pdf"
        file_path = course_dir / filename

        # Save PDF file
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"Saved PDF to: {file_path} (Document ID: {document_id})")
        return str(file_path), document_id

    def _extract_pdf_bytes(self, body: Union[bytes, str, Tuple[str, bytes]]) -> bytes:
        """
        Extract PDF bytes from different input formats.

        Args:
            body: PDF data in various formats

        Returns:
            PDF bytes
        """
        if isinstance(body, tuple):
            # Assume format (filename, pdf_bytes)
            _, pdf_bytes = body
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode()
        elif isinstance(body, bytes):
            pdf_bytes = body
        elif isinstance(body, str):
            # Assume base64 encoded or raw string
            try:
                import base64

                pdf_bytes = base64.b64decode(body)
            except Exception:
                pdf_bytes = body.encode()
        else:
            raise ValueError(f"Unsupported body format: {type(body)}")

        return pdf_bytes

    async def upload_pdf(self, course_id: str, body: Union[bytes, str, Tuple[str, bytes]]) -> str:
        """
        Process and upload PDF to vector database.

        Args:
            course_id: Unique course identifier
            body: PDF file data

        Returns:
            Document ID string
        """
        logger.info(f"Starting PDF upload for course_id: '{course_id}'")

        if not course_id or not course_id.strip():
            raise ValueError("course_id must be a non-empty string")

        try:
            # Step 1: Extract PDF bytes and save file
            pdf_bytes = self._extract_pdf_bytes(body)
            pdf_path, document_id = self._save_pdf(course_id, pdf_bytes)
            logger.info(f"PDF saved with document ID: {document_id}")

            # Step 2: Extract text from slides
            slide_texts = self.text_extractor.extract_text_from_pdf(pdf_path)
            logger.info(f"Extracted text from {len(slide_texts)} slides")

            if not slide_texts:
                logger.warning("No text extracted from PDF")
                # Continue anyway - might have images

            # Step 3: Extract images from PDF
            images_by_page = self.image_extractor.extract_images_grouped(pdf_path)
            total_images = sum(len(page_images) for page_images in images_by_page)
            logger.info(f"Extracted {total_images} images from {len(images_by_page)} pages")

            # Ensure same number of pages for text and images
            max_pages = max(len(slide_texts), len(images_by_page))
            while len(slide_texts) < max_pages:
                slide_texts.append("")
            while len(images_by_page) < max_pages:
                images_by_page.append([])

            # Step 4: Generate image descriptions
            described_images = self.image_descriptor.caption_images_grouped(images_by_page)

            # Step 5: Ingest into vector database
            logger.info("Ingesting data into vector database...")
            await self.ingestion_service.ingest(course_id=course_id, document_id=document_id, slide_texts=slide_texts, slide_images=described_images)

            logger.info(f"PDF upload completed successfully! Document ID: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"PDF upload failed: {e}")
            raise


def get_upload_pdf_service() -> PDFUploadService:
    """Factory function to get PDFUploadService instance."""
    return PDFUploadService()


# Example usage
async def main():
    """Example usage of the PDFUploadService"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Initialize service
    service = PDFUploadService()

    # Example: Upload a PDF file
    try:
        # Simulate PDF upload (you would get this from the API)
        with open("example.pdf", "rb") as f:
            pdf_bytes = f.read()

        document_id = await service.upload_pdf(course_id="CS101_ML_Fundamentals", body=pdf_bytes)

        print("=" * 50)
        print("PDF UPLOAD COMPLETE")
        print("=" * 50)
        print(f"Document ID: {document_id}")
        print("✅ PDF uploaded successfully!")

    except Exception as e:
        print(f"Upload failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
