#!/usr/bin/env python3
"""
Test the actual search_slides_fused_with_images method to see where it fails.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

def test_actual_method():
    """Test the actual search_slides_fused_with_images method."""
    print("=" * 60)
    print("TESTING ACTUAL METHOD")
    print("=" * 60)
    
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:28947")
    store = WeaviateGraphStore(base_url=base_url)
    
    # Create a sample query vector (random 768-dimensional)
    import random
    query_vector = [random.gauss(0, 1) for _ in range(768)]
    
    print(f"Query vector dimensions: {len(query_vector)}")
    print(f"Calling search_slides_fused_with_images with:")
    print(f"  k=3")
    print(f"  alpha=0.8")
    print(f"  similarity_threshold=0.0 (to see all results)")
    
    # Call the actual method
    results = store.search_slides_fused_with_images(
        query_vector=query_vector,
        k=3,
        alpha=0.8,
        similarity_threshold=0.0  # Set to 0 to see all results
    )
    
    print(f"\nGot {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Course: {result.get('courseId')}")
        print(f"  Slide: {result.get('slideNo')}")
        print(f"  Scores: {result.get('scores', {})}")
        print(f"  Images: {len(result.get('images', []))}")
        
        # Check the scores field structure
        scores = result.get('scores', {})
        if scores:
            print(f"  Score details:")
            for key, value in scores.items():
                print(f"    {key}: {value}")

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    try:
        test_actual_method()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()