#!/usr/bin/env python3
"""
Image Extraction Debug Test
"""

import sys
from pathlib import Path
import logging
import base64
import json
from typing import List, Dict, Any
from datetime import datetime
import io
from PIL import Image

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from docint_app.services.pdf_image_extractor_service import get_pdf_image_extractor_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def save_image_from_base64(base64_data: str, output_path: Path) -> None:
    """
    Save base64 image data to a file.
    
    Args:
        base64_data: Base64 encoded image data
        output_path: Path where to save the image
    """
    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_data)
        
        # Open with PIL to determine format and save
        image = Image.open(io.BytesIO(image_bytes))
        
        # Save with original format
        image.save(output_path)
        logger.info(f"💾 Saved image: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save image {output_path}: {e}")


def analyze_and_save_images(pdf_path: str, output_dir: Path) -> None:
    """
    Extract images from PDF and save them for visual inspection.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted images
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract images
    extractor_service = get_pdf_image_extractor_service()
    image_groups = extractor_service.extract_images_grouped(pdf_path)
    
    pdf_name = Path(pdf_path).stem
    total_images = 0
    
    logger.info(f"🔍 Analyzing PDF: {pdf_name}")
    logger.info(f"📊 Total pages: {len(image_groups)}")
    
    for page_number, page_images in enumerate(image_groups, start=1):
        if not page_images:
            logger.info(f"📄 Page {page_number}: No images")
            continue
            
        logger.info(f"📄 Page {page_number}: {len(page_images)} images extracted")
        
        for img_index, img_data in enumerate(page_images, start=1):
            total_images += 1
            
            # Create filename
            filename = f"{pdf_name}_page_{page_number:02d}_img_{img_index:02d}.png"
            output_path = output_dir / filename
            
            # Log image info
            base64_data = img_data['data']
            logger.info(f"  🖼️ Image {img_index}:")
            logger.info(f"    - Base64 length: {len(base64_data)} characters")
            logger.info(f"    - Estimated size: {len(base64_data) * 3 // 4} bytes")
            logger.info(f"    - Saving as: {filename}")
            
            # Save image
            save_image_from_base64(base64_data, output_path)
    
    logger.info(f"✅ Extraction completed!")
    logger.info(f"📊 Total images extracted and saved: {total_images}")
    logger.info(f"📁 Images saved to: {output_dir}")


def main():
    """Main function to extract and save images from all test PDFs."""
    test_dir = Path(__file__).parent
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = test_dir / "extracted_images" / timestamp
    
    # Test PDFs
    pdf_files = [
        "ITP2425 W10U01 Overview.pdf",
        "ITP2425 W10U02 Domain specific languages.pdf", 
        "ITP2425 W10U03 Syntax trees.pdf"
    ]
    
    logger.info(f"🚀 Starting image extraction and visualization")
    logger.info(f"📁 Output directory: {output_dir}")
    
    for pdf_file in pdf_files:
        pdf_path = test_dir / pdf_file
        if pdf_path.exists():
            logger.info(f"\n{'='*60}")
            try:
                analyze_and_save_images(str(pdf_path), output_dir)
            except Exception as e:
                logger.error(f"❌ Failed to process {pdf_file}: {e}")
        else:
            logger.warning(f"⚠️ PDF not found: {pdf_path}")
    
    logger.info(f"\n🎉 All done! Check the images in: {output_dir}")


if __name__ == "__main__":
    main()