"""
PDF Upload Service
Processes PDF files by extracting text and images, generating descriptions, and storing in vector database.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union

from docint_app.services.describe_images_service import get_image_description_service
from docint_app.services.extract_text_service import get_extract_text_service
from docint_app.services.ingestion_service import IngestionService
from docint_app.services.pdf_image_extractor_service import get_pdf_image_extractor_service


class PDFUploadService:
    def __init__(self, base_url: str = "http://docint-weaviate:28947", storage_dir: str = "uploaded_pdfs"):
        """
        Initialize the PDF upload service with all required components.

        Args:
            base_url: Weaviate database URL
            storage_dir: Directory to store uploaded PDFs
        """

        base_url = os.getenv("WEAVIATE_URL", base_url)
        print(f"Initializing PDFUploadService with base_url: {base_url}")
        try:
            self.text_extractor = get_extract_text_service()
            self.image_extractor = get_pdf_image_extractor_service()
            self.image_descriptor = get_image_description_service()
            self.ingestion_service = IngestionService(base_url=base_url)
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(exist_ok=True)
            print("Successfully initialized all PDF processing services")
        except Exception as e:
            print(f"Failed to initialize PDFUploadService: {e}")
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

        print(f"Saved PDF to: {file_path} (Document ID: {document_id})")
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

    async def test_upload_pdf(self) -> str:
        await self.ingestion_service.ingest(
            course_id="test_course",
            document_id="test_document",
            slide_texts=["This is a test slide."],
            slide_images=[
                [
                    {
                        "data": "data:image/jpeg;base64,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", # noqa E501
                        "caption": "Test image caption.",
                    }
                ]
            ],
        )
        return "test_document"

    async def upload_pdf(self, course_id: str, body: Union[bytes, str, Tuple[str, bytes]]) -> str:
        """
        Process and upload PDF to vector database.

        Args:
            course_id: Unique course identifier
            body: PDF file data

        Returns:
            Document ID string
        """
        print(f"Starting PDF upload for course_id: '{course_id}'")

        if not course_id or not course_id.strip():
            raise ValueError("course_id must be a non-empty string")

        try:
            # Step 1: Extract PDF bytes and save file
            pdf_bytes = self._extract_pdf_bytes(body)
            pdf_path, document_id = self._save_pdf(course_id, pdf_bytes)
            print(f"PDF saved with document ID: {document_id}")

            # Step 2: Extract text from slides
            slide_texts = self.text_extractor.extract_text_from_pdf(pdf_path)
            print(f"Extracted text from {len(slide_texts)} slides")

            if not slide_texts:
                print("No text extracted from PDF")
                # Continue anyway - might have images

            # Step 3: Extract images from PDF
            images_by_page = self.image_extractor.extract_images_grouped(pdf_path)
            total_images = sum(len(page_images) for page_images in images_by_page)
            print(f"Extracted {total_images} images from {len(images_by_page)} pages")

            # Ensure same number of pages for text and images
            max_pages = max(len(slide_texts), len(images_by_page))
            while len(slide_texts) < max_pages:
                slide_texts.append("")
            while len(images_by_page) < max_pages:
                images_by_page.append([])

            # Step 4: Generate image descriptions
            described_images = self.image_descriptor.caption_images_grouped(images_by_page)

            # Step 5: Ingest into vector database
            print("Ingesting data into vector database...")
            await self.ingestion_service.ingest(course_id=course_id, document_id=document_id, slide_texts=slide_texts, slide_images=described_images)

            print(f"PDF upload completed successfully! Document ID: {document_id}")
            return document_id

        except Exception as e:
            print(f"PDF upload failed: {e}")
            raise


_instance: Optional[PDFUploadService] = None


def get_upload_pdf_service() -> PDFUploadService:
    """Singleton accessor for PDFUploadService"""
    global _instance
    if _instance is None:
        _instance = PDFUploadService()
    return _instance


# Example usage
async def main() -> None:
    """Example usage of the PDFUploadService"""

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
