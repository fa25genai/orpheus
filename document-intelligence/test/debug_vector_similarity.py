#!/usr/bin/env python3
"""
Debug script to diagnose vector similarity issues in WeaviateGraphStore.

This script will:
1. Test the raw GraphQL queries to see what distances are returned
2. Check the similarity conversion function
3. Examine the fusion logic step by step
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

# Try to import embeddings service
try:
    from docint_app.embeddings.embeddings_service import EmbeddingsService
    HAS_EMBEDDINGS = True
except ImportError:
    print("Warning: Could not import EmbeddingsService, will skip embedding tests")
    HAS_EMBEDDINGS = False

def test_raw_queries():
    """Test the raw GraphQL queries to see what distances are returned."""
    print("=" * 60)
    print("TESTING RAW GRAPHQL QUERIES")
    print("=" * 60)
    
    # Initialize services
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:28947")
    store = WeaviateGraphStore(base_url=base_url)
    
    # Test query
    test_query = "programming languages compiled interpreted Java"
    print(f"Test query: {test_query}")
    
    # Use a sample vector instead of embeddings service
    print("\n1. Using sample query embedding...")
    # Create a random 768-dimensional vector for testing
    import random
    query_embedding = [random.gauss(0, 1) for _ in range(768)]
    print(f"Query embedding dimensions: {len(query_embedding)}")
    print(f"Query embedding first 5 values: {query_embedding[:5]}")
    
    # Test raw GraphQL query for slides
    print("\n2. Testing raw Slide search...")
    gql_slides = f"""
    {{
      Get {{
        Slide(
          nearVector: {{ vector: {json.dumps(list(query_embedding))} }}
          limit: 5
        ) {{
          courseId, documentId, slideNo, slideDescription,
          _additional {{ id, distance, certainty }}
        }}
      }}
    }}
    """
    
    res_slides = store._post("/v1/graphql", {"query": gql_slides})
    slide_hits = res_slides.get("data", {}).get("Get", {}).get("Slide", []) or []
    
    print(f"Found {len(slide_hits)} slides")
    for i, slide in enumerate(slide_hits):
        additional = slide.get("_additional", {})
        distance = additional.get("distance")
        certainty = additional.get("certainty")
        print(f"  Slide {i+1}: slideNo={slide.get('slideNo')}")
        print(f"    Distance: {distance}")
        print(f"    Certainty: {certainty}")
        print(f"    Similarity (our calc): {store._similarity_from_distance(distance)}")
        print(f"    Description preview: {slide.get('slideDescription', '')[:100]}...")
        print()
    
    # Test raw GraphQL query for images
    print("\n3. Testing raw SlideImage search...")
    gql_images = f"""
    {{
      Get {{
        SlideImage(
          nearVector: {{ vector: {json.dumps(list(query_embedding))} }}
          limit: 5
        ) {{
          courseId, documentId, slideNo, description,
          _additional {{ id, distance, certainty }}
        }}
      }}
    }}
    """
    
    res_images = store._post("/v1/graphql", {"query": gql_images})
    image_hits = res_images.get("data", {}).get("Get", {}).get("SlideImage", []) or []
    
    print(f"Found {len(image_hits)} images")
    for i, image in enumerate(image_hits):
        additional = image.get("_additional", {})
        distance = additional.get("distance")
        certainty = additional.get("certainty")
        print(f"  Image {i+1}: slideNo={image.get('slideNo')}")
        print(f"    Distance: {distance}")
        print(f"    Certainty: {certainty}")
        print(f"    Similarity (our calc): {store._similarity_from_distance(distance)}")
        print(f"    Description: {image.get('description', '')[:100]}...")
        print()

def test_similarity_conversion():
    """Test the similarity conversion function with various inputs."""
    print("=" * 60)
    print("TESTING SIMILARITY CONVERSION")
    print("=" * 60)
    
    store = WeaviateGraphStore()
    
    test_distances = [None, 0.0, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, "invalid"]
    
    for dist in test_distances:
        sim = store._similarity_from_distance(dist)
        print(f"Distance: {dist} -> Similarity: {sim}")

def test_fusion_logic():
    """Test the fusion logic step by step."""
    print("=" * 60)
    print("TESTING FUSION LOGIC")
    print("=" * 60)
    
    if not HAS_EMBEDDINGS:
        print("Skipping fusion logic test - no embeddings service available")
        return
    
    base_url = os.getenv("WEAVIATE_URL", "http://localhost:28947")
    store = WeaviateGraphStore(base_url=base_url)
    embeddings_service = EmbeddingsService()
    
    test_query = "programming languages compiled interpreted Java"
    query_embedding = embeddings_service.get_text_embedding(test_query)
    
    print(f"Query: {test_query}")
    print(f"Query embedding dims: {len(query_embedding)}")
    
    # Call the search method with debugging
    print("\n4. Testing full search_slides_fused_with_images method...")
    results = store.search_slides_fused_with_images(
        query_vector=query_embedding,
        k=3,
        similarity_threshold=0.0,  # Set to 0 to see all results
        alpha=0.8
    )
    
    print(f"Got {len(results)} results")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Course: {result.get('courseId')}")
        print(f"  Document: {result.get('documentId')}")
        print(f"  Slide: {result.get('slideNo')}")
        print(f"  Scores: {result.get('scores', {})}")
        print(f"  Images: {len(result.get('images', []))}")
        print(f"  Description: {result.get('slideDescription', '')[:100]}...")

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    try:
        test_raw_queries()
        test_similarity_conversion()
        test_fusion_logic()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()