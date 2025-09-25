"""
Retrieval Service
Searches for slides and images in WeaviateGraphStore using text queries and returns relevant content.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional

from docint_app.services.embedding_service import get_embedding_service
from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RetrievalService:
    def __init__(self, base_url: str = "http://docint-weaviate:28947"):
        """Initialize the retrieval service with Weaviate store and embedding service."""
        base_url = os.getenv("WEAVIATE_URL", base_url)
        logger.info(f"Initializing RetrievalService with base_url: {base_url}")
        
        try:
            self.store = WeaviateGraphStore(base_url=base_url)
            self.embedder = get_embedding_service()
            logger.info("Successfully initialized WeaviateGraphStore and EmbeddingService")
        except Exception as e:
            logger.error(f"Failed to initialize RetrievalService: {e}")
            raise

    async def search(
        self,
        query: str,
        course_id: Optional[str] = None,
        k: int = 5,
        alpha: float = 0.8,
        per_slide_image_agg: str = "max",
        include_images: bool = True
    ) -> Dict[str, Any]:
        """
        Search for slides and images based on a text query.

        Args:
            query: The search query text
            course_id: Optional course ID to filter results
            k: Number of results to return (default: 5)
            alpha: Weight for text vs image similarity (0.8 = 80% text, 20% image)
            per_slide_image_agg: How to aggregate image scores per slide ("max" or "mean")
            include_images: Whether to include image data in response
            
        Returns:
            Dict containing search results, metadata, and statistics
        """
        logger.info(f"Starting search for query: '{query[:80]}...' (course_id={course_id}, k={k})")
        
        # Input validation
        if not query.strip():
            raise ValueError("Query must be a non-empty string")
        
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got: {k}")
        
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be between 0.0 and 1.0, got: {alpha}")

        results = {
            "query": query,
            "course_id": course_id,
            "k": k,
            "alpha": alpha,
            "total_hits": 0,
            "slides": [],
            "content": [],
            "images": [],
            "search_metadata": {
                "query_embedding_dims": 0,
                "fusion_weights": {"text": alpha, "image": 1.0 - alpha},
                "image_aggregation": per_slide_image_agg
            },
            "errors": []
        }

        try:
            # Generate query embedding
            logger.info("Generating embedding for search query...")
            query_vector = await self.embedder.embed_text(query)
            results["search_metadata"]["query_embedding_dims"] = len(query_vector)
            logger.info(f"Generated query embedding with {len(query_vector)} dimensions")

            # Perform fused search
            logger.info(f"Performing fused search (text+image) with alpha={alpha}...")
            slide_hits = self.store.search_slides_fused_with_images(
                query_vector=query_vector,
                course_id=course_id,
                k=k,
                alpha=alpha,
                per_slide_image_agg=per_slide_image_agg,
                include_distance=True
            )
            
            results["total_hits"] = len(slide_hits)
            logger.info(f"Found {len(slide_hits)} slide hits")

            # Process hits
            for i, hit in enumerate(slide_hits):
                logger.debug(f"Processing hit {i+1}: slide {hit.get('slideNo')} from course {hit.get('courseId')}")
                
                slide_info = {
                    "rank": i + 1,
                    "id": hit.get("id"),
                    "course_id": hit.get("courseId"),
                    "document_id": hit.get("documentId"),
                    "slide_no": hit.get("slideNo"),
                    "description": hit.get("slideDescription", ""),
                    "scores": {
                        "fused": hit.get("fusedScore", 0.0),
                        "text_similarity": hit.get("similarityText", 0.0),
                        "image_similarity": hit.get("bestImageSimilarity", 0.0),
                        "text_distance": hit.get("distanceText")
                    },
                    "image_count": len(hit.get("images", []))
                }
                
                results["slides"].append(slide_info)
                
                # Add slide content
                slide_desc = hit.get("slideDescription", "").strip()
                if slide_desc:
                    results["content"].append(slide_desc)
                
                # Add images if requested
                if include_images:
                    for img in hit.get("images", []):
                        if img.get("imageBase64"):
                            results["images"].append({
                                "image": img.get("imageBase64"),
                                "description": img.get("description", ""),
                                "slide_no": hit.get("slideNo"),
                                "course_id": hit.get("courseId")
                            })

            logger.info(f"Search completed. Found {results['total_hits']} slides, "
                       f"{len(results['content'])} content pieces, {len(results['images'])} images")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            results["errors"].append(f"Search error: {e}")
            
        return results

    async def search_simple(
        self,
        query: str,
        course_id: Optional[str] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Simplified search method that returns results in OpenAPI-compatible format.
        
        Args:
            query: The search query text
            course_id: Optional course ID to filter results
            k: Number of results to return
            
        Returns:
            Dict with 'content' and 'images' arrays matching OpenAPI RetrievalResponse
        """
        logger.info(f"Starting simple search for query: '{query[:50]}...'")
        
        # Input validation
        if not query.strip():
            raise ValueError("Query must be a non-empty string")
        
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got: {k}")
        
        try:
            # Generate query embedding
            query_vector = await self.embedder.embed_text(query)
            
            # Perform search
            slide_hits = self.store.search_slides_fused_with_images(
                query_vector=query_vector,
                course_id=course_id,
                k=k,
                alpha=0.8,  # Default text-heavy weighting
                include_distance=False
            )
            logger.info(f"Retrieved {len(slide_hits)} hits from store")
            
            # Convert to OpenAPI format
            response = self.store.to_retrieval_response(slide_hits)
            logger.info(f"Simple search completed. Returning {len(response.get('content', []))} content items, "
                       f"{len(response.get('images', []))} images")
            
            return response
            
        except Exception as e:
            logger.error(f"Simple search failed: {e}")
            return {"content": [], "images": [], "error": str(e)}

    def get_all_course_data(self, course_id: str) -> Dict[str, Any]:
        """Test function: Get all data for a courseId."""
        logger.info(f"Getting all data for course: {course_id}")
        return self.store.get_all_data_for_course(course_id)

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the retrieval service and its dependencies.
        
        Returns:
            Dict containing health status information
        """
        logger.info("Performing health check...")
        
        health_status = {
            "service": "retrieval",
            "status": "unknown",
            "weaviate_ready": False,
            "embedding_service_ready": False,
            "timestamp": None,
            "errors": []
        }
        
        try:
            # Check Weaviate
            health_status["weaviate_ready"] = self.store.is_ready()
            logger.info(f"Weaviate ready: {health_status['weaviate_ready']}")
            
            # Check embedding service (this would require a test call)
            health_status["embedding_service_ready"] = bool(self.embedder)
            logger.info(f"Embedding service ready: {health_status['embedding_service_ready']}")
            
            # Overall status
            if health_status["weaviate_ready"] and health_status["embedding_service_ready"]:
                health_status["status"] = "healthy"
            else:
                health_status["status"] = "unhealthy"
                
            from datetime import datetime
            health_status["timestamp"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["status"] = "error"
            health_status["errors"].append(str(e))
            
        logger.info(f"Health check completed: {health_status['status']}")
        return health_status


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()