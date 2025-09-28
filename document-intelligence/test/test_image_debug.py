#!/usr/bin/env python3
"""
Image Extraction and Captioning Debug Test
Isolates and tests the PDF image extraction and image captioning services to identify specific issues.
"""

import sys
from pathlib import Path
import logging
import base64
import json
from typing import List, Dict, Any

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.pdf_image_extractor_service import get_pdf_image_extractor_service
from docint_app.services.describe_images_service import get_image_description_service

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ImageDebugTest:
    """Debug test for image extraction and captioning services."""
    
    def __init__(self):
        """Initialize debug test with services."""
        logger.info("Initializing Image Debug Test")
        try:
            self.image_extractor = get_pdf_image_extractor_service()
            self.image_descriptor = get_image_description_service()
            logger.info("✅ Successfully initialized image services")
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    def test_single_pdf_image_extraction(self, pdf_path: str) -> List[List[Dict[str, Any]]]:
        """
        Test image extraction from a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of pages with extracted images
        """
        logger.info(f"🔍 Testing image extraction from: {Path(pdf_path).name}")
        
        try:
            # Extract images
            images_by_page = self.image_extractor.extract_images_grouped(pdf_path)
            
            # Analyze results
            total_images = sum(len(page_images) for page_images in images_by_page)
            logger.info(f"📊 Extraction Summary:")
            logger.info(f"   - Total pages: {len(images_by_page)}")
            logger.info(f"   - Total images: {total_images}")
            
            # Analyze each page
            for page_idx, page_images in enumerate(images_by_page, 1):
                if page_images:
                    logger.info(f"   - Page {page_idx}: {len(page_images)} images")
                    
                    # Analyze first image on this page in detail
                    if page_images:
                        self._analyze_image_data(page_images[0], f"Page {page_idx}, Image 1")
                else:
                    logger.debug(f"   - Page {page_idx}: No images")
            
            return images_by_page
            
        except Exception as e:
            logger.error(f"❌ Image extraction failed: {e}")
            raise
    
    def _analyze_image_data(self, image_data: Dict[str, str], label: str) -> None:
        """
        Analyze a single image data structure.
        
        Args:
            image_data: Dictionary containing image data
            label: Label for logging
        """
        logger.info(f"🔬 Analyzing {label}:")
        
        # Check data structure
        if 'data' not in image_data:
            logger.error(f"   ❌ Missing 'data' key in image structure")
            return
        
        data_url = image_data['data']
        logger.info(f"   - Data URL prefix: {data_url[:50]}...")
        
        # Parse data URL
        if not data_url.startswith('data:'):
            logger.error(f"   ❌ Invalid data URL format - doesn't start with 'data:'")
            return
        
        try:
            # Split data URL: data:image/png;base64,<base64_data>
            header, base64_data = data_url.split(',', 1)
            logger.info(f"   - Header: {header}")
            logger.info(f"   - Base64 data length: {len(base64_data)}")
            
            # Check base64 validity
            try:
                decoded_data = base64.b64decode(base64_data, validate=True)
                logger.info(f"   ✅ Base64 decoding successful")
                logger.info(f"   - Decoded size: {len(decoded_data)} bytes")
                
                # Check image format by magic bytes
                self._check_image_format(decoded_data)
                
            except Exception as decode_error:
                logger.error(f"   ❌ Base64 decoding failed: {decode_error}")
                
                # Additional analysis for base64 issues
                logger.info(f"   - Base64 length: {len(base64_data)}")
                logger.info(f"   - Base64 length mod 4: {len(base64_data) % 4}")
                logger.info(f"   - Last 10 chars: {base64_data[-10:]}")
                
        except ValueError as e:
            logger.error(f"   ❌ Failed to split data URL: {e}")
    
    def _check_image_format(self, image_bytes: bytes) -> None:
        """
        Check image format by examining magic bytes.
        
        Args:
            image_bytes: Raw image bytes
        """
        if len(image_bytes) < 8:
            logger.warning(f"   ⚠️  Image too small ({len(image_bytes)} bytes)")
            return
        
        # Check common image formats
        magic_bytes = image_bytes[:8]
        
        if magic_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            logger.info(f"   ✅ Detected PNG format")
        elif magic_bytes.startswith(b'\xff\xd8\xff'):
            logger.info(f"   ✅ Detected JPEG format")
        elif magic_bytes.startswith(b'GIF8'):
            logger.info(f"   ✅ Detected GIF format")
        elif magic_bytes.startswith(b'RIFF') and magic_bytes[8:12] == b'WEBP':
            logger.info(f"   ✅ Detected WebP format")
        else:
            logger.warning(f"   ⚠️  Unknown image format")
            logger.info(f"   - Magic bytes: {magic_bytes.hex()}")
    
    def test_image_captioning(self, images_by_page: List[List[Dict[str, str]]], max_images: int = 3) -> None:
        """
        Test image captioning service with extracted images.
        
        Args:
            images_by_page: Images grouped by page
            max_images: Maximum number of images to test
        """
        logger.info(f"🔍 Testing image captioning (max {max_images} images)")
        
        tested_count = 0
        
        for page_idx, page_images in enumerate(images_by_page, 1):
            if tested_count >= max_images:
                break
                
            for img_idx, image_data in enumerate(page_images, 1):
                if tested_count >= max_images:
                    break
                
                logger.info(f"📝 Testing caption for Page {page_idx}, Image {img_idx}")
                
                try:
                    # Extract base64 data
                    data_url = image_data['data']
                    if ',' in data_url:
                        base64_data = data_url.split(',', 1)[1]
                    else:
                        logger.error(f"   ❌ Invalid data URL format")
                        continue
                    
                    # Test caption generation
                    caption = self.image_descriptor._get_image_caption(base64_data)
                    
                    if caption:
                        logger.info(f"   ✅ Caption generated: '{caption[:100]}...'")
                    else:
                        logger.warning(f"   ⚠️  Empty caption returned")
                    
                    tested_count += 1
                    
                except Exception as e:
                    logger.error(f"   ❌ Caption generation failed: {e}")
                    tested_count += 1
    
    def test_all_pdfs(self, max_images_per_pdf: int = 2) -> None:
        """
        Test image extraction and captioning for all PDFs in test directory.
        
        Args:
            max_images_per_pdf: Maximum images to test captioning per PDF
        """
        test_dir = Path(__file__).parent
        pdf_files = list(test_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning("No PDF files found in test directory")
            return
        
        logger.info(f"🚀 Testing {len(pdf_files)} PDF files")
        
        for pdf_file in pdf_files:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {pdf_file.name}")
            logger.info(f"{'='*60}")
            
            try:
                # Test extraction
                images_by_page = self.test_single_pdf_image_extraction(str(pdf_file))
                
                # Test captioning with limited images
                if any(images_by_page):
                    self.test_image_captioning(images_by_page, max_images_per_pdf)
                else:
                    logger.info("   ℹ️  No images to test captioning")
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {pdf_file.name}: {e}")
    
    def save_debug_sample(self, pdf_path: str, output_file: str = "debug_image_sample.json") -> None:
        """
        Save a sample of extracted image data for debugging.
        
        Args:
            pdf_path: Path to PDF file
            output_file: Output JSON file name
        """
        logger.info(f"💾 Saving debug sample to {output_file}")
        
        try:
            images_by_page = self.image_extractor.extract_images_grouped(pdf_path)
            
            # Create debug sample with first few images
            debug_data = {
                "pdf_file": Path(pdf_path).name,
                "total_pages": len(images_by_page),
                "total_images": sum(len(page) for page in images_by_page),
                "sample_images": []
            }
            
            sample_count = 0
            for page_idx, page_images in enumerate(images_by_page, 1):
                for img_idx, image_data in enumerate(page_images, 1):
                    if sample_count >= 3:  # Limit to 3 samples
                        break
                    
                    # Create sample with truncated data for readability
                    data_url = image_data['data']
                    if ',' in data_url:
                        header, base64_data = data_url.split(',', 1)
                        sample = {
                            "page": page_idx,
                            "image": img_idx,
                            "header": header,
                            "base64_length": len(base64_data),
                            "base64_sample": base64_data[:100] + "..." if len(base64_data) > 100 else base64_data,
                            "base64_ending": "..." + base64_data[-20:] if len(base64_data) > 100 else "",
                            "length_mod_4": len(base64_data) % 4
                        }
                        debug_data["sample_images"].append(sample)
                        sample_count += 1
                
                if sample_count >= 3:
                    break
            
            # Save to file
            output_path = Path(__file__).parent / output_file
            with open(output_path, 'w') as f:
                json.dump(debug_data, f, indent=2)
            
            logger.info(f"✅ Debug sample saved to {output_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save debug sample: {e}")


def main():
    """Main test execution."""
    logger.info("🚀 Starting Image Extraction and Captioning Debug Test")
    
    try:
        # Initialize test
        test = ImageDebugTest()
        
        # Test all PDFs
        test.test_all_pdfs(max_images_per_pdf=2)
        
        # Save debug sample from first PDF found
        test_dir = Path(__file__).parent
        pdf_files = list(test_dir.glob("*.pdf"))
        if pdf_files:
            test.save_debug_sample(str(pdf_files[0]))
        
        logger.info("✅ Debug test completed")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()