#!/usr/bin/env python3
"""
Simple focused debug to test just the vector similarity calculation.
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

def test_score_calculation():
    """Test the score calculation logic step by step."""
    print("=" * 60)
    print("TESTING SCORE CALCULATION")
    print("=" * 60)
    
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:28947")
    store = WeaviateGraphStore(base_url=base_url)
    
    # Create a sample query vector (random 768-dimensional)
    import random
    query_vector = [random.gauss(0, 1) for _ in range(768)]
    
    print(f"Query vector dimensions: {len(query_vector)}")
    print(f"Query vector first 5 values: {query_vector[:5]}")

    # Test 1: Raw GraphQL slide search
    print("\n1. Testing raw slide search...")
    gql_slides = f"""
    {{
      Get {{
        Slide(
          nearVector: {{ vector: {json.dumps(list(query_vector))} }}
          limit: 3
        ) {{
          courseId, documentId, slideNo, slideDescription,
          _additional {{ id, distance, certainty }}
        }}
      }}
    }}
    """
    
    res_slides = store._post("/v1/graphql", {"query": gql_slides})
    slide_hits = res_slides.get("data", {}).get("Get", {}).get("Slide", []) or []
    
    print(f"Found {len(slide_hits)} slides:")
    text_scores = {}
    slide_meta = {}
    
    for s in slide_hits:
        key = (s.get("courseId"), s.get("slideNo"))
        dist = (s.get("_additional") or {}).get("distance")
        similarity = store._similarity_from_distance(dist)
        text_scores[key] = similarity
        slide_meta[key] = s
        
        print(f"  Slide {s.get('slideNo')}: distance={dist}, similarity={similarity}")
        print(f"    Key: {key}")
        print(f"    Description: {s.get('slideDescription', '')[:80]}...")
    
    print(f"\ntext_scores dict: {text_scores}")
    
    # Test 2: Raw GraphQL image search
    print("\n2. Testing raw image search...")
    gql_images = f"""
    {{
      Get {{
        SlideImage(
          nearVector: {{ vector: {json.dumps(list(query_vector))} }}
          limit: 3
        ) {{
          courseId, documentId, slideNo, description,
          _additional {{ id, distance, certainty }}
        }}
      }}
    }}
    """
    
    res_images = store._post("/v1/graphql", {"query": gql_images})
    image_hits = res_images.get("data", {}).get("Get", {}).get("SlideImage", []) or []
    
    print(f"Found {len(image_hits)} images:")
    from collections import defaultdict
    per_slide_image_sims = defaultdict(list)
    
    for im in image_hits:
        key = (im.get("courseId"), im.get("slideNo"))
        dist = (im.get("_additional") or {}).get("distance")
        similarity = store._similarity_from_distance(dist) 
        per_slide_image_sims[key].append(similarity)
        
        print(f"  Image for slide {im.get('slideNo')}: distance={dist}, similarity={similarity}")
        print(f"    Key: {key}")
        print(f"    Description: {im.get('description', '')[:80]}...")
    
    # Aggregate image scores per slide
    image_scores = {
        key: max(vals) for key, vals in per_slide_image_sims.items() if vals
    }
    print(f"\nimage_scores dict: {image_scores}")
    
    # Test 3: Score fusion
    print("\n3. Testing score fusion...")
    fused_scores = {}
    all_slide_keys = set(text_scores.keys()) | set(image_scores.keys())
    alpha = 0.8
    
    for key in all_slide_keys:
        text_sim = text_scores.get(key, 0.0)
        image_sim = image_scores.get(key, 0.0)
        fused_score = (alpha * text_sim) + ((1.0 - alpha) * image_sim)
        fused_scores[key] = fused_score
        
        print(f"  Key {key}: text={text_sim:.4f}, image={image_sim:.4f}, fused={fused_score:.4f}")
    
    print(f"\nfused_scores dict: {fused_scores}")
    
    # Test 4: Filtering by threshold
    print("\n4. Testing threshold filtering...")
    similarity_threshold = 0.3
    relevant_slides = {key: score for key, score in fused_scores.items() if score >= similarity_threshold}
    print(f"Relevant slides (>= {similarity_threshold}): {relevant_slides}")
    
    # Sort and get top results
    sorted_slides = sorted(relevant_slides.items(), key=lambda item: item[1], reverse=True)
    top_keys = [key for key, score in sorted_slides[:3]]
    print(f"Top 3 keys: {top_keys}")
    
    # Test 5: Final result assembly
    print("\n5. Testing final result assembly...")
    for i, key in enumerate(top_keys):
        c_id, s_no = key
        final_fused_score = fused_scores.get(key, 0.0)
        final_text_sim = text_scores.get(key, 0.0)
        final_image_sim = image_scores.get(key, 0.0)
        
        print(f"  Result {i+1}:")
        print(f"    Key: {key}")
        print(f"    Fused: {final_fused_score}")
        print(f"    Text: {final_text_sim}")
        print(f"    Image: {final_image_sim}")

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    try:
        test_score_calculation()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()