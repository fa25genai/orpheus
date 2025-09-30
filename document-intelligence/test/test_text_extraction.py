#!/usr/bin/env python3
"""
Text Extraction Service Test
Tests the text extraction service with the 3 test PDFs.
Shows detailed text extraction results for each slide to verify quality.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.extract_text_service import get_extract_text_service

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


class TextExtractionTest:
    """Test class for text extraction service."""
    
    def __init__(self, test_folder: str):
        """
        Initialize test with test folder path.
        
        Args:
            test_folder: Path to folder containing test PDF files
        """
        self.test_folder = Path(test_folder)
        self.text_service = get_extract_text_service()
        self.test_results = {
            "test_metadata": {
                "start_time": datetime.now().isoformat(),
                "test_folder": str(self.test_folder),
                "test_name": "Text Extraction Service Test"
            },
            "tested_pdfs": [],
            "statistics": {
                "total_pdfs": 0,
                "total_slides": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "empty_extractions": 0
            }
        }
    
    def test_single_pdf(self, pdf_path: Path, max_text_display: int = 300) -> Dict[str, Any]:
        """
        Test text extraction for a single PDF.
        
        Args:
            pdf_path: Path to PDF file
            max_text_display: Maximum characters to display per slide in logs
            
        Returns:
            Dictionary with test results
        """
        logger.info(f"📄 Testing PDF: {pdf_path.name}")
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return {
                "pdf_name": pdf_path.name,
                "success": False,
                "error": "File not found",
                "slides": [],
                "total_slides": 0,
                "file_size": 0
            }
        
        file_size = pdf_path.stat().st_size
        logger.info(f"   📏 File size: {file_size:,} bytes")
        
        try:
            # Extract text from all slides
            logger.info(f"   🔄 Extracting text from slides...")
            extracted_texts = self.text_service.extract_text_from_pdf(str(pdf_path))
            
            if not extracted_texts:
                logger.warning(f"   ⚠️  No text extracted from PDF")
                self.test_results["statistics"]["failed_extractions"] += 1
                return {
                    "pdf_name": pdf_path.name,
                    "success": False,
                    "error": "No text extracted",
                    "slides": [],
                    "total_slides": 0,
                    "file_size": file_size
                }
            
            # Process each slide's text
            slides_data = []
            for i, slide_text in enumerate(extracted_texts, 1):
                slide_text_clean = slide_text.strip()
                text_length = len(slide_text_clean)
                is_empty = text_length == 0
                
                if is_empty:
                    self.test_results["statistics"]["empty_extractions"] += 1
                    logger.warning(f"   📝 Slide {i:2d}: ⚠️  Empty text extracted")
                else:
                    self.test_results["statistics"]["successful_extractions"] += 1
                    display_text = slide_text_clean[:max_text_display]
                    if len(slide_text_clean) > max_text_display:
                        display_text += "..."
                    logger.info(f"   📝 Slide {i:2d}: ({text_length:4d} chars) {display_text}")
                
                slides_data.append({
                    "slide_number": i,
                    "text": slide_text_clean,
                    "text_length": text_length,
                    "is_empty": is_empty,
                    "preview": slide_text_clean[:100] + ("..." if len(slide_text_clean) > 100 else "")
                })
            
            total_slides = len(extracted_texts)
            self.test_results["statistics"]["total_slides"] += total_slides
            
            logger.info(f"   ✅ Extracted text from {total_slides} slides")
            
            return {
                "pdf_name": pdf_path.name,
                "success": True,
                "error": None,
                "slides": slides_data,
                "total_slides": total_slides,
                "file_size": file_size,
                "total_characters": sum(slide["text_length"] for slide in slides_data),
                "empty_slides": sum(1 for slide in slides_data if slide["is_empty"]),
                "non_empty_slides": sum(1 for slide in slides_data if not slide["is_empty"])
            }
            
        except Exception as e:
            logger.error(f"   ❌ Text extraction failed: {e}")
            self.test_results["statistics"]["failed_extractions"] += 1
            return {
                "pdf_name": pdf_path.name,
                "success": False,
                "error": str(e),
                "slides": [],
                "total_slides": 0,
                "file_size": file_size
            }
    
    def test_all_pdfs(self, max_pdfs: int | None = None) -> None:
        """
        Test text extraction for all PDFs in the test folder.
        
        Args:
            max_pdfs: Maximum number of PDFs to test (None for all)
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
        
        logger.info(f"🚀 Testing text extraction from {len(pdf_files)} PDFs")
        self.test_results["statistics"]["total_pdfs"] = len(pdf_files)
        
        # Test each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"PDF {i}/{len(pdf_files)}: {pdf_file.name}")
            logger.info(f"{'='*80}")
            
            result = self.test_single_pdf(pdf_file)
            self.test_results["tested_pdfs"].append(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test summary."""
        stats = self.test_results["statistics"]
        
        print(f"\n{'='*80}")
        print("TEXT EXTRACTION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total PDFs Tested: {stats['total_pdfs']}")
        print(f"Total Slides: {stats['total_slides']}")
        print(f"Successful Extractions: {stats['successful_extractions']}")
        print(f"Failed Extractions: {stats['failed_extractions']}")
        print(f"Empty Extractions: {stats['empty_extractions']}")
        
        if stats['total_slides'] > 0:
            success_rate = (stats['successful_extractions'] / stats['total_slides']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"\nDetailed Results by PDF:")
        for result in self.test_results["tested_pdfs"]:
            if result["success"]:
                total_chars = result["total_characters"]
                non_empty = result["non_empty_slides"]
                total_slides = result["total_slides"]
                avg_chars = total_chars / non_empty if non_empty > 0 else 0
                
                print(f"  📄 {result['pdf_name']}:")
                print(f"     Slides: {total_slides} total, {non_empty} with text, {result['empty_slides']} empty")
                print(f"     Characters: {total_chars:,} total, {avg_chars:.0f} avg per non-empty slide")
                print(f"     File size: {result['file_size']:,} bytes")
            else:
                print(f"  ❌ {result['pdf_name']}: {result['error']}")
        
        print(f"{'='*80}")
    
    def save_detailed_results(self, output_file: str | None = None) -> None:
        """
        Save detailed test results to JSON file.
        
        Args:
            output_file: Output filename (auto-generated if None)
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"text_extraction_test_{timestamp}.json"
        
        output_path = Path(__file__).parent / "logs" / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        # Add end time
        self.test_results["test_metadata"]["end_time"] = datetime.now().isoformat()
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            logger.info(f"📄 Detailed results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def save_text_extracts(self, output_dir: str | None = None) -> None:
        """
        Save extracted text for each PDF and slide to separate files for detailed review.
        
        Args:
            output_dir: Output directory (auto-generated if None)
        """
        if not output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"text_extracts_{timestamp}"
        
        output_path = Path(__file__).parent / "logs" / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            for pdf_result in self.test_results["tested_pdfs"]:
                if not pdf_result["success"]:
                    continue
                
                pdf_name = pdf_result["pdf_name"].replace(".pdf", "")
                pdf_folder = output_path / pdf_name
                pdf_folder.mkdir(exist_ok=True)
                
                # Save individual slide texts
                for slide in pdf_result["slides"]:
                    slide_num = slide["slide_number"]
                    slide_file = pdf_folder / f"slide_{slide_num:02d}.txt"
                    
                    with open(slide_file, 'w', encoding='utf-8') as f:
                        f.write(f"PDF: {pdf_result['pdf_name']}\n")
                        f.write(f"Slide: {slide_num}\n")
                        f.write(f"Characters: {slide['text_length']}\n")
                        f.write(f"Empty: {slide['is_empty']}\n")
                        f.write("-" * 50 + "\n\n")
                        f.write(slide["text"])
                
                # Save combined PDF text
                combined_file = pdf_folder / f"{pdf_name}_combined.txt"
                with open(combined_file, 'w', encoding='utf-8') as f:
                    f.write(f"PDF: {pdf_result['pdf_name']}\n")
                    f.write(f"Total Slides: {pdf_result['total_slides']}\n")
                    f.write(f"Total Characters: {pdf_result['total_characters']}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for slide in pdf_result["slides"]:
                        f.write(f"SLIDE {slide['slide_number']}\n")
                        f.write("-" * 20 + "\n")
                        f.write(slide["text"])
                        f.write("\n\n" + "=" * 80 + "\n\n")
            
            logger.info(f"📄 Text extracts saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save text extracts: {e}")


def main():
    """Main test execution."""
    logger.info("🚀 Starting Text Extraction Service Test")
    
    # Set up test folder path
    test_folder = Path(__file__).parent
    
    try:
        # Check if API key is properly configured
        if os.getenv('OLLAMA_API_KEY') == 'your-ollama-api-key-here':
            logger.error("❌ OLLAMA_API_KEY not properly configured. Please set it in environment or .env file")
            return
        
        # Initialize test
        test = TextExtractionTest(str(test_folder))
        
        # Test all PDFs (or limit with max_pdfs=1 for quick testing)
        test.test_all_pdfs(max_pdfs=None)  # Change to a number to limit testing
        
        # Save results
        test.save_detailed_results()
        test.save_text_extracts()
        
        logger.info("✅ Text extraction test completed")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
