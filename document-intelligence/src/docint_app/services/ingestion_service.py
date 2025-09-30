"""
Ingestion Service
Takes parsed slides (text + images), generates embeddings, and stores them in WeaviateGraphStore.
"""

import os
from typing import Any, Dict, List, Optional, TypedDict

from docint_app.services.embedding_service import get_embedding_service
from docint_app.vectorstore.weaviate_graph_store import get_store


class _IngestResults(TypedDict):
    course_id: str
    document_id: str
    total_slides: int
    processed_slides: int
    total_images: int
    processed_images: int
    slide_uuids: List[str]
    image_ids: List[str]
    errors: List[str]


class IngestionService:
    def __init__(self, base_url: str = "http://docint-weaviate:28947"):
        """Initialize the ingestion service with Weaviate store and embedding service."""
        base_url = os.getenv("WEAVIATE_URL", base_url)
        print(f"Initializing IngestionService with base_url: {base_url}")
        try:
            self.store = get_store()
            self.embedder = get_embedding_service()
            print("Successfully initialized WeaviateGraphStore and EmbeddingService")
        except Exception as e:
            print(f"Failed to initialize IngestionService: {e}")
            raise

    async def ingest(
        self,
        course_id: str,
        document_id: str,
        slide_texts: List[str],
        slide_images: List[List[Dict[str, Any]]],
    ) -> _IngestResults:
        """
        Ingest slides + images into Weaviate.

        Args:
            course_id: Unique course identifier
            document_id: Unique document identifier
            slide_texts: List of slide texts, index = slide number - 1
            slide_images: List of lists, each entry is [] or [{data, caption}, ...]

        Returns:
            Dict containing ingestion results and statistics
        """
        print(f"Starting ingestion for course_id='{course_id}', document_id='{document_id}'")
        print(f"Processing {len(slide_texts)} slides")

        # Validate inputs
        if not course_id or not document_id:
            raise ValueError("course_id and document_id must be non-empty strings")

        if len(slide_texts) != len(slide_images):
            raise ValueError(f"Slide texts ({len(slide_texts)}) and images ({len(slide_images)}) must align")

        results: _IngestResults = {
            "course_id": course_id,
            "document_id": document_id,
            "total_slides": len(slide_texts),
            "processed_slides": 0,
            "total_images": sum(len(images) for images in slide_images),
            "processed_images": 0,
            "slide_uuids": [],
            "image_ids": [],
            "errors": [],
        }

        try:
            # 1. Ensure schema exists
            print("Ensuring Weaviate schema exists...")
            self.store.ensure_schema()
            print("Schema validation completed")

            # 2. Embed all slide texts
            print(f"Generating embeddings for {len(slide_texts)} slide texts...")
            text_vectors = self.embedder.embed_batch(slide_texts)
            print(f"Generated {len(text_vectors)} text embeddings")
        except Exception as e:
            print(f"Failed during initial setup: {e}")
            results["errors"].append(f"Setup error: {e}")
            return results

        for slide_no, (text, vec, images) in enumerate(zip(slide_texts, text_vectors, slide_images), start=1):
            print(f"Processing slide {slide_no}/{len(slide_texts)}")
            print(f"Slide text preview: {text[:80]}...")
            print(f"Text vector dimensions: {len(vec) if vec else 0}")

            try:
                # Upsert Slide
                print(f"Upserting slide {slide_no} to Weaviate...")
                slide_uuid = self.store.upsert_slide(
                    course_id=course_id,
                    document_id=document_id,
                    slide_no=slide_no,
                    slide_description=text,
                    text_vector=vec,
                )
                print(f"Successfully upserted slide {slide_no}, UUID: {slide_uuid}")
                results["slide_uuids"].append(slide_uuid)
                results["processed_slides"] += 1

                # Handle images
                if images:
                    print(f"Processing {len(images)} image(s) for slide {slide_no}")
                    try:
                        captions = [img.get("caption", "") for img in images]
                        print(f"Image captions: {captions}")

                        if any(captions):  # Only generate embeddings if we have captions
                            caption_vecs = self.embedder.embed_batch(captions)
                            print(f"Generated {len(caption_vecs)} caption embeddings")
                        else:
                            caption_vecs = [[0.0] * len(vec)] * len(images)
                            print(f"No captions found for images in slide {slide_no}, using zero vectors")

                        # pair embeddings with image data
                        img_payloads = [(img.get("data", ""), img.get("caption", "")) for img in images]

                        created_ids = self.store.upsert_images_and_link(
                            course_id=course_id,
                            document_id=document_id,
                            slide_no=slide_no,
                            images=img_payloads,
                            image_description="",
                            text_vector=caption_vecs[0] if caption_vecs else [0.0] * len(vec),
                            slide_uuid=slide_uuid,
                        )
                        print(f"Successfully linked {len(created_ids)} images for slide {slide_no}: {created_ids}")
                        results["image_ids"].extend(created_ids)
                        results["processed_images"] += len(created_ids)

                    except Exception as e:
                        print(f"Failed to process images for slide {slide_no}: {e}")
                        results["errors"].append(f"Slide {slide_no} image processing error: {e}")

                else:
                    print(f"Slide {slide_no} has no images")

            except Exception as e:
                print(f"Failed to process slide {slide_no}: {e}")
                results["errors"].append(f"Slide {slide_no} processing error: {e}")

        print(f"Ingestion completed. Processed {results['processed_slides']}/{results['total_slides']} slides, {results['processed_images']}/{results['total_images']} images")

        if results["errors"]:
            print(f"Ingestion completed with {len(results['errors'])} errors")

        return results


_instance: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    global _instance
    if _instance is None:
        _instance = IngestionService()
    return _instance
