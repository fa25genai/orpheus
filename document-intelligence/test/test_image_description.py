#!/usr/bin/env python3
"""
Image Description Service Test
Tests the image captioning service with extracted images from the 3 test PDFs.
Reads saved images and generates captions to verify the service functionality.
"""

import sys
import os
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.describe_images_service import get_image_description_service

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


class ImageDescriptionTest:
    """Test class for image description service."""
    
    def __init__(self, images_folder: str):
        """
        Initialize test with images folder path.
        
        Args:
            images_folder: Path to folder containing extracted images
        """
        self.images_folder = Path(images_folder)
        self.description_service = get_image_description_service()
        self.test_results = {
            "test_metadata": {
                "start_time": datetime.now().isoformat(),
                "images_folder": str(self.images_folder),
                "test_name": "Image Description Service Test"
            },
            "tested_images": [],
            "statistics": {
                "total_images": 0,
                "successful_captions": 0,
                "failed_captions": 0,
                "empty_captions": 0
            }
        }
    
    def load_image_as_base64(self, image_path: Path) -> str:
        """
        Load an image file and convert to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return ""
    
    def parse_filename(self, filename: str) -> Dict[str, Any]:
        """
        Parse the filename to extract PDF name, page, and image info.
        
        Args:
            filename: Image filename (e.g., "ITP2425 W10U01 Overview_page_01_img_01.png")
            
        Returns:
            Dictionary with parsed information
        """
        try:
            # Remove extension
            name_without_ext = filename.rsplit('.', 1)[0]
            
            # Find the last occurrence of '_page_' to split correctly
            if '_page_' not in name_without_ext:
                raise ValueError("Expected '_page_' in filename")
            
            # Split at the last '_page_'
            page_split = name_without_ext.rsplit('_page_', 1)
            pdf_name = page_split[0]
            page_and_img = page_split[1]  # e.g., "01_img_01"
            
            # Split the page and image part
            if '_img_' not in page_and_img:
                raise ValueError("Expected '_img_' in filename")
            
            page_img_parts = page_and_img.split('_img_')
            page_num = int(page_img_parts[0])  # "01" -> 1
            img_num = int(page_img_parts[1])   # "01" -> 1
            
            return {
                "pdf_name": pdf_name,
                "page": page_num,
                "image": img_num,
                "filename": filename
            }
        except Exception as e:
            logger.warning(f"Could not parse filename {filename}: {e}")
            return {
                "pdf_name": "unknown",
                "page": 0,
                "image": 0,
                "filename": filename
            }
    
    def test_single_image(self, image_path: Path, max_caption_length: int = 200) -> Dict[str, Any]:
        """
        Test captioning for a single image.
        
        Args:
            image_path: Path to image file
            max_caption_length: Maximum length to display in logs
            
        Returns:
            Dictionary with test results
        """
        logger.info(f"🖼️  Testing: {image_path.name}")
        
        # Parse filename
        file_info = self.parse_filename(image_path.name)
        
        # Load image
        base64_image = self.load_image_as_base64(image_path)
        if not base64_image:
            return {
                **file_info,
                "success": False,
                "error": "Failed to load image",
                "caption": "",
                "file_size": 0
            }
        
        file_size = image_path.stat().st_size
        
        try:
            # Check if API key is properly set
            if os.getenv('OLLAMA_API_KEY') == 'your-ollama-api-key-here':
                logger.warning(f"   ⚠️  OLLAMA_API_KEY not properly configured. Skipping caption generation.")
                self.test_results["statistics"]["failed_captions"] += 1
                return {
                    **file_info,
                    "success": False,
                    "error": "OLLAMA_API_KEY not configured",
                    "caption": "",
                    "caption_length": 0,
                    "file_size": file_size
                }
            
            # Generate caption
            logger.info(f"   📝 Generating caption...")
            caption = self.description_service._get_image_caption(base64_image)
            
            success = bool(caption and caption.strip())
            
            if success:
                logger.info(f"   ✅ Caption: {caption[:max_caption_length]}{'...' if len(caption) > max_caption_length else ''}")
                self.test_results["statistics"]["successful_captions"] += 1
            elif caption == "":
                logger.warning(f"   ⚠️  Empty caption returned")
                self.test_results["statistics"]["empty_captions"] += 1
            else:
                logger.warning(f"   ⚠️  Invalid caption: {caption}")
                self.test_results["statistics"]["failed_captions"] += 1
            
            return {
                **file_info,
                "success": success,
                "error": None,
                "caption": caption,
                "caption_length": len(caption),
                "file_size": file_size
            }
            
        except Exception as e:
            logger.error(f"   ❌ Caption generation failed: {e}")
            self.test_results["statistics"]["failed_captions"] += 1
            return {
                **file_info,
                "success": False,
                "error": str(e),
                "caption": "",
                "caption_length": 0,
                "file_size": file_size
            }
    
    def test_all_images(self, max_images: int | None = None) -> None:
        """
        Test captioning for all images in the folder.
        
        Args:
            max_images: Maximum number of images to test (None for all)
        """
        if not self.images_folder.exists():
            logger.error(f"Images folder not found: {self.images_folder}")
            return
        
        # Get all image files
        image_files = list(self.images_folder.glob("*.png")) + list(self.images_folder.glob("*.jpg")) + list(self.images_folder.glob("*.jpeg"))
        
        if not image_files:
            logger.warning(f"No image files found in {self.images_folder}")
            return
        
        # Sort by filename for consistent order
        image_files.sort()
        
        # Limit if requested
        if max_images:
            image_files = image_files[:max_images]
        
        logger.info(f"🚀 Testing {len(image_files)} images from {self.images_folder}")
        self.test_results["statistics"]["total_images"] = len(image_files)
        
        # Group by PDF for better organization
        pdf_groups = {}
        for img_file in image_files:
            file_info = self.parse_filename(img_file.name)
            pdf_name = file_info["pdf_name"]
            if pdf_name not in pdf_groups:
                pdf_groups[pdf_name] = []
            pdf_groups[pdf_name].append(img_file)
        
        # Test each PDF group
        for pdf_name, pdf_images in pdf_groups.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing PDF: {pdf_name} ({len(pdf_images)} images)")
            logger.info(f"{'='*60}")
            
            for img_file in pdf_images:
                result = self.test_single_image(img_file)
                self.test_results["tested_images"].append(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test summary."""
        stats = self.test_results["statistics"]
        
        print(f"\n{'='*80}")
        print("IMAGE DESCRIPTION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Images Tested: {stats['total_images']}")
        print(f"Successful Captions: {stats['successful_captions']}")
        print(f"Failed Captions: {stats['failed_captions']}")
        print(f"Empty Captions: {stats['empty_captions']}")
        
        if stats['total_images'] > 0:
            success_rate = (stats['successful_captions'] / stats['total_images']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        # Group results by PDF
        pdf_results = {}
        for result in self.test_results["tested_images"]:
            pdf_name = result["pdf_name"]
            if pdf_name not in pdf_results:
                pdf_results[pdf_name] = {"total": 0, "success": 0}
            pdf_results[pdf_name]["total"] += 1
            if result["success"]:
                pdf_results[pdf_name]["success"] += 1
        
        print(f"\nResults by PDF:")
        for pdf_name, stats in pdf_results.items():
            success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {pdf_name}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        print(f"{'='*80}")
    
    def save_results(self, output_file: str | None = None) -> None:
        """
        Save test results to JSON file.
        
        Args:
            output_file: Output filename (auto-generated if None)
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"image_description_test_{timestamp}.json"
        
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


def main():
    """Main test execution."""
    logger.info("🚀 Starting Image Description Service Test")
    
    # Set up images folder path
    images_folder = "/Users/raj.vasani/Developer/fa25/orpheus/document-intelligence/test/extracted_images/20250928_145314/"
    
    try:
        # Initialize test
        test = ImageDescriptionTest(images_folder)
        
        # Test all images (or limit with max_images=5 for quick testing)
        test.test_all_images(max_images=None)  # Change to a number to limit testing
        
        # Save results
        test.save_results()
        
        logger.info("✅ Image description test completed")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()

