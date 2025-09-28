#!/usr/bin/env python3
"""
Ingestion Service Test
Tests the complete ingestion pipeline by uploading PDFs from the test folder to the database.
This test verifies that the full document processing pipeline works correctly.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.pdf_upload_service import PDFUploadService
from docint_app.services.ingestion_service import IngestionService
from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IngestionTest:
    """Test class for comprehensive ingestion service testing."""
    
    def __init__(self, base_url: str = "http://localhost:28947"):
        """
        Initialize test with database connection.
        
        Args:
            base_url: Weaviate database URL (use localhost for local testing)
        """
        self.base_url = base_url
        self.pdf_upload_service = PDFUploadService(base_url=base_url)
        self.ingestion_service = IngestionService(base_url=base_url)
        self.graph_store = WeaviateGraphStore(base_url=base_url)
        
        self.test_start_time = datetime.now()
        self.test_results = {
            "test_metadata": {
                "start_time": self.test_start_time.isoformat(),
                "test_name": "Ingestion Service Test",
                "test_version": "1.0",
                "description": "Test complete PDF ingestion pipeline",
                "database_url": base_url
            },
            "processed_pdfs": [],
            "errors": [],
            "statistics": {
                "total_pdfs": 0,
                "successful_uploads": 0,
                "failed_uploads": 0,
                "total_slides": 0,
                "total_images": 0
            }
        }
    
    async def check_database_connection(self) -> bool:
        """
        Check if database is ready and accessible.
        
        Returns:
            True if database is ready, False otherwise
        """
        logger.info("Checking database connection...")
        try:
            is_ready = self.graph_store.is_ready()
            if is_ready:
                logger.info("✅ Database is ready and accessible")
                return True
            else:
                logger.error("❌ Database is not ready")
                return False
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def process_all_pdfs(self) -> None:
        """Process all PDF files in the test directory."""
        test_dir = Path(__file__).parent
        pdf_files = list(test_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning("No PDF files found in test directory")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        self.test_results["statistics"]["total_pdfs"] = len(pdf_files)
        
        for i, pdf_file in enumerate(pdf_files, 1):
            await self._process_single_pdf(pdf_file, i, len(pdf_files))
    
    async def _process_single_pdf(self, pdf_file: Path, current: int, total: int) -> None:
        """
        Process a single PDF file through the complete ingestion pipeline.
        
        Args:
            pdf_file: Path to PDF file
            current: Current file number
            total: Total number of files
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing PDF {current}/{total}: {pdf_file.name}")
        logger.info(f"{'='*60}")
        
        # Prepare course_id from filename (remove extension and clean up)
        course_id = pdf_file.stem.replace(" ", "_").replace("-", "_")
        
        pdf_result = {
            "filename": pdf_file.name,
            "course_id": course_id,
            "file_size_bytes": pdf_file.stat().st_size,
            "processing_start": datetime.now().isoformat(),
            "document_id": None,
            "success": False,
            "error": None,
            "slides_processed": 0,
            "images_processed": 0
        }
        
        try:
            # Read PDF file
            with open(pdf_file, "rb") as f:
                pdf_data = f.read()
            
            logger.info(f"📄 File size: {len(pdf_data):,} bytes")
            
            # Upload and process PDF through the complete pipeline
            logger.info("🚀 Starting upload and ingestion process...")
            document_id = await self.pdf_upload_service.upload_pdf(
                course_id=course_id,
                body=pdf_data
            )
            
            pdf_result["document_id"] = document_id
            pdf_result["success"] = True
            pdf_result["processing_end"] = datetime.now().isoformat()
            
            # Verify ingestion by checking database
            await self._verify_ingestion(course_id, document_id, pdf_result)
            
            logger.info(f"✅ Successfully processed {pdf_file.name}")
            logger.info(f"📊 Document ID: {document_id}")
            
            self.test_results["statistics"]["successful_uploads"] += 1
            
        except Exception as e:
            error_msg = f"Failed to process {pdf_file.name}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            pdf_result["error"] = error_msg
            pdf_result["processing_end"] = datetime.now().isoformat()
            
            self.test_results["errors"].append(error_msg)
            self.test_results["statistics"]["failed_uploads"] += 1
        
        finally:
            self.test_results["processed_pdfs"].append(pdf_result)
    
    async def _verify_ingestion(self, course_id: str, document_id: str, pdf_result: Dict) -> None:
        """
        Verify that the PDF was properly ingested into the database.
        
        Args:
            course_id: Course identifier
            document_id: Document identifier
            pdf_result: Result dictionary to update with verification info
        """
        logger.info("🔍 Verifying ingestion in database...")
        
        try:
            # Get all data for this course from database
            course_data = self.graph_store.get_all_data_for_course(course_id)
            
            slides = course_data.get("slides", [])
            images = course_data.get("images", [])
            
            # Count slides and images for this specific document
            doc_slides = [s for s in slides if s.get("documentId") == document_id]
            doc_images = [img for img in images if img.get("documentId") == document_id]
            
            pdf_result["slides_processed"] = len(doc_slides)
            pdf_result["images_processed"] = len(doc_images)
            
            self.test_results["statistics"]["total_slides"] += len(doc_slides)
            self.test_results["statistics"]["total_images"] += len(doc_images)
            
            logger.info(f"📊 Verification complete:")
            logger.info(f"   - Slides in database: {len(doc_slides)}")
            logger.info(f"   - Images in database: {len(doc_images)}")
            
            if len(doc_slides) > 0:
                logger.info("✅ Slides successfully stored in database")
            else:
                logger.warning("⚠️  No slides found in database for this document")
            
            if len(doc_images) > 0:
                logger.info("✅ Images successfully stored in database")
            else:
                logger.info("ℹ️  No images found in database for this document")
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            pdf_result["verification_error"] = str(e)
    
    def print_summary(self) -> None:
        """Print a comprehensive test summary."""
        end_time = datetime.now()
        duration = end_time - self.test_start_time
        
        stats = self.test_results["statistics"]
        
        print(f"\n{'='*80}")
        print("INGESTION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Test Duration: {duration}")
        print(f"Total PDFs: {stats['total_pdfs']}")
        print(f"Successful Uploads: {stats['successful_uploads']}")
        print(f"Failed Uploads: {stats['failed_uploads']}")
        print(f"Total Slides Processed: {stats['total_slides']}")
        print(f"Total Images Processed: {stats['total_images']}")
        
        if stats['total_pdfs'] > 0:
            success_rate = (stats['successful_uploads'] / stats['total_pdfs']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"\nProcessed Files:")
        for pdf in self.test_results["processed_pdfs"]:
            status = "✅" if pdf["success"] else "❌"
            print(f"{status} {pdf['filename']} - Slides: {pdf['slides_processed']}, Images: {pdf['images_processed']}")
        
        if self.test_results["errors"]:
            print(f"\nErrors ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"❌ {error}")
        
        print(f"{'='*80}")
        
        # Update test results with final metadata
        self.test_results["test_metadata"]["end_time"] = end_time.isoformat()
        self.test_results["test_metadata"]["duration_seconds"] = duration.total_seconds()
    
    def save_results(self) -> None:
        """Save test results to a JSON file."""
        timestamp = self.test_start_time.strftime("%Y%m%d_%H%M%S")
        results_file = Path(__file__).parent / "logs" / f"ingestion_test_{timestamp}.json"
        
        # Ensure logs directory exists
        results_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(results_file, "w") as f:
                json.dump(self.test_results, f, indent=2)
            logger.info(f"📄 Test results saved to: {results_file}")
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")


async def main():
    """Main test execution function."""
    logger.info("Starting Ingestion Service Test")
    logger.info(f"Test started at: {datetime.now()}")
    
    # Initialize test
    test = IngestionTest()
    
    # Check database connection first
    if not await test.check_database_connection():
        logger.error("Cannot proceed with test - database is not accessible")
        logger.error("Make sure Weaviate is running with: docker-compose up -d")
        return
    
    try:
        # Process all PDFs
        await test.process_all_pdfs()
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with unexpected error: {e}")
    finally:
        # Always print summary and save results
        test.print_summary()
        test.save_results()


if __name__ == "__main__":
    asyncio.run(main())