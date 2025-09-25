"""
Ingestion Service
Takes parsed slides (text + images), generates embeddings, and stores them in WeaviateGraphStore.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from docint_app.services.embedding_service import get_embedding_service
from docint_app.vectorstore.weaviate_graph_store import WeaviateGraphStore

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IngestionService:
    def __init__(self, base_url: str = "http://localhost:28947"):
        """Initialize the ingestion service with Weaviate store and embedding service."""
        logger.info(f"Initializing IngestionService with base_url: {base_url}")
        try:
            self.store = WeaviateGraphStore(base_url=base_url)
            self.embedder = get_embedding_service()
            logger.info("Successfully initialized WeaviateGraphStore and EmbeddingService")
        except Exception as e:
            logger.error(f"Failed to initialize IngestionService: {e}")
            raise

    async def ingest(
        self,
        course_id: str,
        document_id: str,
        slide_texts: List[str],
        slide_images: List[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Ingest slides + images into Weaviate.

        Args:
            course_id: Unique course identifier
            document_id: Unique document identifier
            slide_texts: List of slide texts, index = slide number - 1
            slide_images: List of lists, each entry is [] or [{data, mime_type, caption}, ...]
            
        Returns:
            Dict containing ingestion results and statistics
        """
        logger.info(f"Starting ingestion for course_id='{course_id}', document_id='{document_id}'")
        logger.info(f"Processing {len(slide_texts)} slides")
        
        # Validate inputs
        if not course_id or not document_id:
            raise ValueError("course_id and document_id must be non-empty strings")
        
        if len(slide_texts) != len(slide_images):
            raise ValueError(f"Slide texts ({len(slide_texts)}) and images ({len(slide_images)}) must align")

        results = {
            "course_id": course_id,
            "document_id": document_id,
            "total_slides": len(slide_texts),
            "processed_slides": 0,
            "total_images": sum(len(images) for images in slide_images),
            "processed_images": 0,
            "slide_uuids": [],
            "image_ids": [],
            "errors": []
        }

        try:
            # 1. Ensure schema exists
            logger.info("Ensuring Weaviate schema exists...")
            self.store.ensure_schema()
            logger.info("Schema validation completed")

            # 2. Embed all slide texts
            logger.info(f"Generating embeddings for {len(slide_texts)} slide texts...")
            text_vectors = await self.embedder.embed_batch(slide_texts)
            logger.info(f"Generated {len(text_vectors)} text embeddings")
        except Exception as e:
            logger.error(f"Failed during initial setup: {e}")
            results["errors"].append(f"Setup error: {e}")
            return results

        for slide_no, (text, vec, images) in enumerate(zip(slide_texts, text_vectors, slide_images), start=1):
            logger.info(f"Processing slide {slide_no}/{len(slide_texts)}")
            logger.debug(f"Slide text preview: {text[:80]}...")
            logger.debug(f"Text vector dimensions: {len(vec) if vec else 0}")

            try:
                # Upsert Slide 
                logger.debug(f"Upserting slide {slide_no} to Weaviate...")
                slide_uuid = self.store.upsert_slide(
                    course_id=course_id,
                    document_id=document_id,
                    slide_no=slide_no,
                    slide_description=text,
                    text_vector=vec,
                )
                logger.info(f"Successfully upserted slide {slide_no}, UUID: {slide_uuid}")
                results["slide_uuids"].append(slide_uuid)
                results["processed_slides"] += 1

                # Handle images
                if images:
                    logger.info(f"Processing {len(images)} image(s) for slide {slide_no}")
                    try:
                        captions = [img.get("caption", "") for img in images]
                        logger.debug(f"Image captions: {captions}")
                        
                        if any(captions):  # Only generate embeddings if we have captions
                            caption_vecs = await self.embedder.embed_batch(captions)
                            logger.debug(f"Generated {len(caption_vecs)} caption embeddings")
                        else:
                            caption_vecs = [[0.0] * len(vec)] * len(images)
                            logger.warning(f"No captions found for images in slide {slide_no}, using zero vectors")

                        # pair embeddings with image data
                        img_payloads = [
                            (img.get("data", ""), img.get("caption", "")) for img in images
                        ]

                        created_ids = self.store.upsert_images_and_link(
                            course_id=course_id,
                            document_id=document_id,
                            slide_no=slide_no,
                            images=img_payloads,
                            image_description="",
                            text_vector=caption_vecs[0] if caption_vecs else [0.0] * len(vec),
                            slide_uuid=slide_uuid,
                        )
                        logger.info(f"Successfully linked {len(created_ids)} images for slide {slide_no}: {created_ids}")
                        results["image_ids"].extend(created_ids)
                        results["processed_images"] += len(created_ids)
                        
                    except Exception as e:
                        logger.error(f"Failed to process images for slide {slide_no}: {e}")
                        results["errors"].append(f"Slide {slide_no} image processing error: {e}")
                        
                else:
                    logger.debug(f"Slide {slide_no} has no images")
                    
            except Exception as e:
                logger.error(f"Failed to process slide {slide_no}: {e}")
                results["errors"].append(f"Slide {slide_no} processing error: {e}")

        logger.info(f"Ingestion completed. Processed {results['processed_slides']}/{results['total_slides']} slides, "
                   f"{results['processed_images']}/{results['total_images']} images")
        
        if results["errors"]:
            logger.warning(f"Ingestion completed with {len(results['errors'])} errors")
        
        return results

def get_ingestion_service() -> IngestionService:
    return IngestionService()
