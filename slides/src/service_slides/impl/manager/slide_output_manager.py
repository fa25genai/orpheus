import os
from typing import List


def save_slides_to_file(lecture_id: str, slides: List[str], output_dir: str = "data") -> str:
    """Simple function to save slides to markdown file."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Concatenate with two empty lines between slides
    combined_content = "\n\n\n".join(slides)
    
    # Save to file
    filename = f"{lecture_id}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(combined_content)
    
    print(f"[SlideOutput] Saved {len(slides)} slides to {filepath}")
    return filepath
