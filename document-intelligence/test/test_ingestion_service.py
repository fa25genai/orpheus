#!/usr/bin/env python3
"""
Ingestion Service Test
Tests the complete ingestion pipeline: PDF -> Text Extraction -> Image Extraction -> Image Captioning -> Embedding -> Database Storage
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.extract_text_service import get_extract_text_service
from docint_app.services.pdf_image_extractor_service import get_pdf_image_extractor_service
from docint_app.services.describe_images_service import get_image_description_service
from docint_app.services.ingestion_service import get_ingestion_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set up environment variables if not already set
if not os.getenv('OLLAMA_API_KEY'):
    # Try to load from .env file or set a default
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith('OLLAMA_API_KEY'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
                    break
    else:
        # Set a placeholder - this will need to be replaced with actual key
        logger.warning("OLLAMA_API_KEY not found. Please set it in environment or .env file")
        os.environ['OLLAMA_API_KEY'] = 'your-ollama-api-key-here'


class IngestionServiceTest:
    """Test class for the complete ingestion service pipeline."""
    
    def __init__(self, test_folder: str):
        """
        Initialize test with test folder path.
        
        Args:
            test_folder: Path to folder containing test PDF files
        """
        self.test_folder = Path(test_folder)
        self.text_service = get_extract_text_service()
        self.image_service = get_pdf_image_extractor_service()
        self.caption_service = get_image_description_service()
        
        # Override Weaviate URL to use localhost instead of docker hostname
        os.environ['WEAVIATE_URL'] = 'http://localhost:28947'
        self.ingestion_service = get_ingestion_service()
        
        self.test_results = {
            "test_metadata": {
                "start_time": datetime.now().isoformat(),
                "test_folder": str(self.test_folder),
                "test_name": "Ingestion Service Test"
            },
            "tested_pdfs": [],
            "statistics": {
                "total_pdfs": 0,
                "successful_ingestions": 0,
                "failed_ingestions": 0,
                "total_slides": 0,
                "total_images": 0,
                "slides_in_db": 0,
                "images_in_db": 0
            }
        }
    
    async def process_single_pdf(self, pdf_path: Path, course_id: str = "test_course") -> Dict[str, Any]:
        """
        Process a single PDF through the entire ingestion pipeline.
        
        Args:
            pdf_path: Path to PDF file
            course_id: Course identifier
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"📄 Processing PDF: {pdf_path.name}")
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return {
                "pdf_name": pdf_path.name,
                "success": False,
                "error": "File not found",
                "stage": "file_check",
                "slides": [],
                "images": [],
                "ingestion_results": None
            }
        
        document_id = pdf_path.stem  # Use filename without extension as document ID
        file_size = pdf_path.stat().st_size
        logger.info(f"   📏 File size: {file_size:,} bytes")
        logger.info(f"   🆔 Document ID: {document_id}")
        
        try:
            # Stage 1: Extract text from slides
            logger.info(f"   🔤 Stage 1: Extracting text from slides...")
            slide_texts = self.text_service.extract_text_from_pdf(str(pdf_path))
            
            if not slide_texts:
                logger.error(f"   ❌ No text extracted from PDF")
                return {
                    "pdf_name": pdf_path.name,
                    "success": False,
                    "error": "No text extracted",
                    "stage": "text_extraction",
                    "slides": [],
                    "images": [],
                    "ingestion_results": None
                }
            
            logger.info(f"   ✅ Extracted text from {len(slide_texts)} slides")
            
            # Stage 2: Extract images from slides
            logger.info(f"   🖼️  Stage 2: Extracting images from slides...")
            pdf_images_by_slide = self.image_service.extract_images_grouped(str(pdf_path))
            total_images = sum(len(slide_images) for slide_images in pdf_images_by_slide)
            
            # Ensure we have the right number of slide image lists
            while len(pdf_images_by_slide) < len(slide_texts):
                pdf_images_by_slide.append([])  # Add empty lists for slides with no images
            
            for slide_no, slide_images in enumerate(pdf_images_by_slide, 1):
                logger.debug(f"      Slide {slide_no}: {len(slide_images)} images")
            
            logger.info(f"   ✅ Extracted {total_images} images across {len(slide_texts)} slides")
            
            # Stage 3: Generate captions for images
            logger.info(f"   📝 Stage 3: Generating captions for {total_images} images...")
            slide_images_with_captions = []
            
            for slide_no, slide_images in enumerate(pdf_images_by_slide, 1):
                captioned_images = []
                for img_idx, image_dict in enumerate(slide_images):
                    try:
                        # Extract base64 string from the image dictionary
                        image_base64 = image_dict.get("data", "")
                        if not image_base64:
                            logger.warning(f"      Slide {slide_no}, Image {img_idx + 1}: No image data found")
                            caption = ""
                        else:
                            caption = self.caption_service._get_image_caption(image_base64)
                        
                        captioned_images.append({
                            "data": image_base64,
                            "caption": caption,
                            "slide_no": slide_no,
                            "image_idx": img_idx + 1
                        })
                        logger.debug(f"      Slide {slide_no}, Image {img_idx + 1}: Caption generated ({len(caption)} chars)")
                    except Exception as e:
                        logger.warning(f"      Slide {slide_no}, Image {img_idx + 1}: Caption failed - {e}")
                        captioned_images.append({
                            "data": image_dict.get("data", ""),
                            "caption": "",
                            "slide_no": slide_no,
                            "image_idx": img_idx + 1
                        })
                
                slide_images_with_captions.append(captioned_images)
            
            successful_captions = sum(1 for slide_images in slide_images_with_captions 
                                    for img in slide_images if img["caption"])
            logger.info(f"   ✅ Generated {successful_captions}/{total_images} successful captions")
            
            # Stage 4: Ingest into database
            logger.info(f"   💾 Stage 4: Ingesting into database...")
            ingestion_results = await self.ingestion_service.ingest(
                course_id=course_id,
                document_id=document_id,
                slide_texts=slide_texts,
                slide_images=slide_images_with_captions
            )
            
            logger.info(f"   ✅ Ingestion completed:")
            logger.info(f"      Slides processed: {ingestion_results['processed_slides']}/{ingestion_results['total_slides']}")
            logger.info(f"      Images processed: {ingestion_results['processed_images']}/{ingestion_results['total_images']}")
            logger.info(f"      Errors: {len(ingestion_results['errors'])}")
            
            if ingestion_results['errors']:
                for error in ingestion_results['errors']:
                    logger.warning(f"      ⚠️  {error}")
            
            # Update statistics
            self.test_results["statistics"]["total_slides"] += len(slide_texts)
            self.test_results["statistics"]["total_images"] += total_images
            self.test_results["statistics"]["slides_in_db"] += ingestion_results['processed_slides']
            self.test_results["statistics"]["images_in_db"] += ingestion_results['processed_images']
            
            success = (ingestion_results['processed_slides'] == len(slide_texts) and 
                      len(ingestion_results['errors']) == 0)
            
            if success:
                logger.info(f"   🎉 PDF {pdf_path.name} successfully processed!")
                self.test_results["statistics"]["successful_ingestions"] += 1
            else:
                logger.warning(f"   ⚠️  PDF {pdf_path.name} processed with issues")
                self.test_results["statistics"]["failed_ingestions"] += 1
            
            return {
                "pdf_name": pdf_path.name,
                "document_id": document_id,
                "success": success,
                "error": None,
                "stage": "completed",
                "file_size": file_size,
                "slides": [
                    {
                        "slide_no": i + 1,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "text_length": len(text),
                        "images": len(slide_images_with_captions[i]) if i < len(slide_images_with_captions) else 0
                    }
                    for i, text in enumerate(slide_texts)
                ],
                "images": [
                    {
                        "slide_no": img["slide_no"],
                        "image_idx": img["image_idx"],
                        "has_caption": bool(img["caption"]),
                        "caption_preview": img["caption"][:100] + "..." if len(img["caption"]) > 100 else img["caption"]
                    }
                    for slide_images in slide_images_with_captions
                    for img in slide_images
                ],
                "ingestion_results": ingestion_results
            }
            
        except Exception as e:
            logger.error(f"   ❌ Processing failed: {e}")
            self.test_results["statistics"]["failed_ingestions"] += 1
            return {
                "pdf_name": pdf_path.name,
                "success": False,
                "error": str(e),
                "stage": "processing_error",
                "slides": [],
                "images": [],
                "ingestion_results": None
            }
    
    async def test_all_pdfs(self, max_pdfs: int | None = None, course_id: str = "test_course") -> None:
        """
        Test ingestion for all PDFs in the test folder.
        
        Args:
            max_pdfs: Maximum number of PDFs to test (None for all)
            course_id: Course identifier for all PDFs
        """
        if not self.test_folder.exists():
            logger.error(f"Test folder not found: {self.test_folder}")
            return
        
        # Get all PDF files
        pdf_files = list(self.test_folder.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.test_folder}")
            return
        
        # Sort by filename for consistent order
        pdf_files.sort()
        
        # Limit if requested
        if max_pdfs:
            pdf_files = pdf_files[:max_pdfs]
        
        logger.info(f"🚀 Testing ingestion for {len(pdf_files)} PDFs")
        self.test_results["statistics"]["total_pdfs"] = len(pdf_files)
        
        # Test each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"PDF {i}/{len(pdf_files)}: {pdf_file.name}")
            logger.info(f"{'='*80}")
            
            result = await self.process_single_pdf(pdf_file, course_id)
            self.test_results["tested_pdfs"].append(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test summary."""
        stats = self.test_results["statistics"]
        
        print(f"\n{'='*80}")
        print("INGESTION SERVICE TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total PDFs Tested: {stats['total_pdfs']}")
        print(f"Successful Ingestions: {stats['successful_ingestions']}")
        print(f"Failed Ingestions: {stats['failed_ingestions']}")
        print(f"Total Slides: {stats['total_slides']}")
        print(f"Slides in Database: {stats['slides_in_db']}")
        print(f"Total Images: {stats['total_images']}")
        print(f"Images in Database: {stats['images_in_db']}")
        
        if stats['total_pdfs'] > 0:
            success_rate = (stats['successful_ingestions'] / stats['total_pdfs']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if stats['total_slides'] > 0:
            slide_success_rate = (stats['slides_in_db'] / stats['total_slides']) * 100
            print(f"Slide Storage Rate: {slide_success_rate:.1f}%")
        
        if stats['total_images'] > 0:
            image_success_rate = (stats['images_in_db'] / stats['total_images']) * 100
            print(f"Image Storage Rate: {image_success_rate:.1f}%")
        
        print(f"\nDetailed Results by PDF:")
        for result in self.test_results["tested_pdfs"]:
            if result["success"]:
                ingestion = result["ingestion_results"]
                print(f"  ✅ {result['pdf_name']}:")
                print(f"     Slides: {len(result['slides'])} total, {ingestion['processed_slides']} in DB")
                print(f"     Images: {len(result['images'])} total, {ingestion['processed_images']} in DB")
                if ingestion['errors']:
                    print(f"     Errors: {len(ingestion['errors'])}")
                    for error in ingestion['errors'][:3]:  # Show first 3 errors
                        print(f"       - {error}")
            else:
                print(f"  ❌ {result['pdf_name']}: {result['error']} (Stage: {result['stage']})")
        
        print(f"{'='*80}")
    
    def save_results(self, output_file: str | None = None) -> None:
        """
        Save test results to JSON file.
        
        Args:
            output_file: Output filename (auto-generated if None)
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ingestion_service_test_{timestamp}.json"
        
        output_path = Path(__file__).parent / "logs" / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        # Add end time
        self.test_results["test_metadata"]["end_time"] = datetime.now().isoformat()
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            logger.info(f"📄 Test results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    async def verify_database_content(self, course_id: str = "test_course") -> Dict[str, Any]:
        """
        Verify that the data was actually stored in the database.
        
        Args:
            course_id: Course identifier to check
            
        Returns:
            Dictionary with database verification results
        """
        logger.info(f"🔍 Verifying database content for course: {course_id}")
        
        try:
            # Get all data for the course from database
            db_data = self.ingestion_service.store.get_all_data_for_course(course_id)
            
            slides_in_db = db_data.get("slides", [])
            images_in_db = db_data.get("images", [])
            
            logger.info(f"   📊 Database contains:")
            logger.info(f"      Slides: {len(slides_in_db)}")
            logger.info(f"      Images: {len(images_in_db)}")
            
            # Group slides by document
            slides_by_doc = {}
            for slide in slides_in_db:
                doc_id = slide.get("documentId", "unknown")
                if doc_id not in slides_by_doc:
                    slides_by_doc[doc_id] = []
                slides_by_doc[doc_id].append(slide)
            
            # Group images by document and slide
            images_by_doc_slide = {}
            for image in images_in_db:
                doc_id = image.get("documentId", "unknown")
                slide_no = image.get("slideNo", 0)
                key = f"{doc_id}_slide_{slide_no}"
                if key not in images_by_doc_slide:
                    images_by_doc_slide[key] = []
                images_by_doc_slide[key].append(image)
            
            logger.info(f"   📚 Documents in database:")
            for doc_id, doc_slides in slides_by_doc.items():
                logger.info(f"      {doc_id}: {len(doc_slides)} slides")
                # Count images for this document
                doc_images = sum(len(images) for key, images in images_by_doc_slide.items() 
                               if key.startswith(f"{doc_id}_"))
                logger.info(f"         {doc_images} images total")
            
            return {
                "total_slides": len(slides_in_db),
                "total_images": len(images_in_db),
                "documents": len(slides_by_doc),
                "slides_by_document": {doc_id: len(slides) for doc_id, slides in slides_by_doc.items()},
                "images_by_document": {},  # Could be computed if needed
                "database_data": db_data
            }
            
        except Exception as e:
            logger.error(f"Failed to verify database content: {e}")
            return {
                "error": str(e),
                "total_slides": 0,
                "total_images": 0,
                "documents": 0
            }


async def main():
    """Main test execution."""
    logger.info("🚀 Starting Ingestion Service Test")
    
    # Set up test folder path
    test_folder = Path(__file__).parent
    
    try:
        # Check if API key is properly configured
        if os.getenv('OLLAMA_API_KEY') == 'your-ollama-api-key-here':
            logger.error("❌ OLLAMA_API_KEY not properly configured. Please set it in environment or .env file")
            return
        
        # Initialize test
        test = IngestionServiceTest(str(test_folder))
        
        # Test all PDFs (or limit with max_pdfs=1 for quick testing)
        await test.test_all_pdfs(max_pdfs=1, course_id="test_course_w10")  # Change to a number to limit testing
        
        # Verify database content
        db_verification = await test.verify_database_content("test_course_w10")
        logger.info(f"📊 Database verification: {db_verification.get('total_slides', 0)} slides, {db_verification.get('total_images', 0)} images")
        
        # Save results
        test.save_results()
        
        logger.info("✅ Ingestion service test completed")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
