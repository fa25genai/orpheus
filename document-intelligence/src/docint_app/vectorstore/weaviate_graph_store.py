"""
WeaviateGraphStore — graph-first vector store wrapper (requests-based)

- Schema:
  Slide (vectorized with text embedding)
    - courseId: text
    - documentId: text
    - slideNo: int
    - title: text
    - body: text
    - captionsText: text (optional fused image captions)
    - images: [SlideImage]  <-- cross-reference (graph edge)

  SlideImage (image b64 strings; image vector optional later)
    - courseId: text
    - documentId: text
    - slideNo: int
    - imageBase64: text
    - description: text

  VideoChunk (vectorized with text embedding from transcription)
    - courseId: text (mandatory)
    - chunkId: text (unique identifier)
    - text: text (chunk content from transcription)

- Key ops:
  * ensure_schema()               -> idempotent schema creation + reference property
  * upsert_slide(...)             -> create/replace Slide with text vector
  * upsert_images_and_link(...)   -> create SlideImage objects + link to Slide.images
  * search_slides_with_images(...) -> single GraphQL query: ANN + traverse images
  * upsert_video_chunk(...)       -> create/replace VideoChunk with text vector
  * search_video_chunks(...)      -> search VideoChunk objects by similarity
  * to_retrieval_response(...)    -> map hits -> OpenAPI RetrievalResponse

Notes:
- BYO embeddings: send your text vector when upserting Slide or VideoChunk.
- Vectors are stored in the class's ANN index, keyed by UUID (not a user-defined property).
- This uses raw REST/GraphQL; no weaviate-client dependency required.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests
import weaviate
from weaviate.classes.query import Filter, MetadataQuery

from docint_app.services.embedding_service import get_embedding_service


class WeaviateError(RuntimeError):
    pass


class WeaviateGraphStore:
    def __init__(
        self,
        base_url: str = "http://docint-weaviate:28947",
        api_key: Optional[str] = None,
        timeout_s: int = 15,
    ):
        """
        :param base_url: Weaviate HTTP endpoint (e.g., http://localhost:28947 or http://<host-ip>:28947)
        :param api_key:  Optional API key (if we enable auth later)
        :param timeout_s: Default request timeout
        """
        base_url = os.getenv("WEAVIATE_URL", base_url)
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if api_key:
            # If we enable API key auth later
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    # Health / helpers
    def is_ready(self) -> bool:
        """Check /v1/.well-known/ready until it returns 200 OK."""
        url = f"{self.base_url}/v1/.well-known/ready"
        try:
            r = self.session.get(url, timeout=self.timeout_s)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _raise_for_bad(self, r: requests.Response, what: str) -> None:
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise WeaviateError(f"{what} failed ({r.status_code}): {detail}")

    def _get(self, path: str) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}{path}", timeout=self.timeout_s)
        self._raise_for_bad(r, f"GET {path}")
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self.session.post(f"{self.base_url}{path}", data=json.dumps(payload), timeout=self.timeout_s)
        self._raise_for_bad(r, f"POST {path}")
        if r.text.strip():
            return r.json()
        return {}

    def _put(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self.session.put(f"{self.base_url}{path}", data=json.dumps(payload), timeout=self.timeout_s)
        self._raise_for_bad(r, f"PUT {path}")
        if r.text.strip():
            return r.json()
        return {}

    def _delete(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        r = self.session.delete(f"{self.base_url}{path}", data=(json.dumps(payload) if payload is not None else None), timeout=self.timeout_s)
        self._raise_for_bad(r, f"DELETE {path}")
        return r.json() if r.text.strip() else {}

    @staticmethod
    def _similarity_from_distance(distance: Optional[float]) -> float:
        """
        Convert a Weaviate distance value into a similarity score.

        - Weaviate typically reports cosine distances in [0, 2] (often ~[0, 1] if vectors are normalized).
        - Uses the transform sim = 1 / (1 + distance), which is monotonic and ensures
          that higher similarity corresponds to lower distance.
        - Returns 0.0 if distance is missing or invalid.
        """
        if distance is None:
            return 0.0
        try:
            return 1.0 / (1.0 + float(distance))
        except Exception:
            return 0.0

    @staticmethod
    def _minmax_normalize(scores: Dict[tuple, float]) -> Dict[tuple, float]:
        """
        Normalize a dictionary of scores to the range [0, 1] using min–max scaling.

        - Input: dict mapping (courseId, slideNo) keys to raw scores.
        - If all values are equal, maps every entry to 1.0 to avoid divide-by-zero
          and prevent an entire channel from collapsing to zero weight.
        - Returns a dict of the same shape with normalized scores.
        """
        if not scores:
            return {}
        vals = list(scores.values())
        lo, hi = min(vals), max(vals)
        if hi <= lo:
            # all equal → map to 1.0 (best) to avoid zeroing the whole channel
            return {k: 1.0 for k in scores}
        span = hi - lo
        return {k: (v - lo) / span for k, v in scores.items()}

    def _fetch_all_images_for_slide(self, course_id: str, slide_no: int, limit: int = 64) -> List[Dict[str, Any]]:
        """
        Fetch all SlideImage objects for a given slide (courseId + slideNo).

        - Issues a GraphQL query filtering by courseId and slideNo.
        - Returns a list of dicts containing description, imageBase64, and _additional metadata.
        - `limit` controls the maximum number of images retrieved (default = 64).
        """
        gql = f"""
        {{
          Get {{
            SlideImage(
              where: {{
                operator: And
                operands: [
                  {{ operator: Equal, path: ["courseId"], valueText: "{course_id}" }},
                  {{ operator: Equal, path: ["slideNo"],  valueInt: {int(slide_no)} }}
                ]
              }}
              limit: {int(limit)}
            ) {{
              description
              imageBase64
              _additional {{ id }}
            }}
          }}
        }}
        """
        res = self._post("/v1/graphql", {"query": gql})
        return res.get("data", {}).get("Get", {}).get("SlideImage", []) or []

    # Schema
    def ensure_schema(self) -> None:
        """
        Create classes if missing and ensure Slide has a reference property 'images' to SlideImage.

        Uses REST schema endpoints:
        - GET  /v1/schema
        - POST /v1/schema/{className}
        - POST /v1/schema/{className}/properties  (for adding the reference)
        """
        # current schema
        schema = self._get("/v1/schema")
        existing_classes = {c["class"] for c in schema.get("classes", [])}

        # create SlideImage first (so Slide can reference it)
        if "SlideImage" not in existing_classes:
            self._post(
                "/v1/schema",
                {
                    "class": "SlideImage",
                    "description": "Images extracted from slides (image vector optional)",
                    "vectorizer": "none",
                    "properties": [
                        {"name": "courseId", "dataType": ["text"]},
                        {"name": "documentId", "dataType": ["text"]},
                        {"name": "slideNo", "dataType": ["int"]},
                        {"name": "imageBase64", "dataType": ["text"]},
                        {"name": "description", "dataType": ["text"]},
                        {"name": "createdAt", "dataType": ["date"]},
                        {"name": "modifiedAt", "dataType": ["date"]},
                    ],
                },
            )

        # create VideoChunk (standalone, no references)
        if "VideoChunk" not in existing_classes:
            self._post(
                "/v1/schema",
                {
                    "class": "VideoChunk",
                    "description": "Video transcription chunks (vectorized with text embedding)",
                    "vectorizer": "none",  # BYO vectors
                    "properties": [
                        {"name": "courseId", "dataType": ["text"]},
                        {"name": "lectureId", "dataType": ["text"]},
                        {"name": "chunkId", "dataType": ["text"]},
                        {"name": "text", "dataType": ["text"]},
                    ],
                },
            )

        # Refresh classes set
        schema = self._get("/v1/schema")
        existing_classes = {c["class"] for c in schema.get("classes", [])}

        # create Slide (without the reference first)
        if "Slide" not in existing_classes:
            self._post(
                "/v1/schema",
                {
                    "class": "Slide",
                    "description": "One per slide: text + fused captions (vectorized) and a ref to images",
                    "vectorizer": "none",  # BYO vectors
                    "properties": [
                        {"name": "courseId", "dataType": ["text"]},
                        {"name": "documentId", "dataType": ["text"]},
                        {"name": "slideNo", "dataType": ["int"]},
                        {"name": "slideDescription", "dataType": ["text"]},
                        {"name": "createdAt", "dataType": ["date"]},
                        {"name": "modifiedAt", "dataType": ["date"]},
                    ],
                },
            )

        # ensure Slide has 'images' reference to SlideImage
        slide_schema = next(
            (c for c in self._get("/v1/schema").get("classes", []) if c["class"] == "Slide"),
            None,
        )
        prop_names = {p["name"] for p in slide_schema.get("properties", [])} if slide_schema else set()
        if "images" not in prop_names:
            self._post(
                "/v1/schema/Slide/properties",
                {
                    "name": "images",
                    "dataType": ["SlideImage"],  # cross-reference
                    "description": "References from a slide to its images",
                },
            )

    # Upserts (objects + vectors + references)
    @staticmethod
    def _default_slide_uuid(document_id: str, slide_no: int) -> str:
        # Deterministic UUIDv5 from stable natural key
        name = f"Slide::{document_id}::{slide_no:04d}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, name))

    @staticmethod
    def _default_image_uuid(document_id: str, slide_no: int, idx: int) -> str:
        name = f"SlideImage::{document_id}::{slide_no:04d}::img::{idx:02d}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, name))

    def upsert_slide(
        self,
        *,
        course_id: str,
        document_id: str,
        slide_no: int,
        slide_description: str,
        text_vector: Sequence[float],
        created_at_iso: Optional[str] = None,
        modified_at_iso: Optional[str] = None,
        slide_uuid: Optional[str] = None,
    ) -> str:
        """
        Create/replace a Slide object with its text embedding (BYO vector).
        Uses POST to create; on conflict falls back to PUT to update (idempotent).
        :return: UUID used for the slide
        """
        uid = slide_uuid or self._default_slide_uuid(document_id, slide_no)
        payload = {
            "class": "Slide",
            "id": uid,
            "properties": {
                "courseId": course_id,
                "documentId": document_id,
                "slideNo": slide_no,
                "slideDescription": slide_description,
            },
            "vector": list(text_vector),
        }
        if created_at_iso:
            payload["properties"]["createdAt"] = created_at_iso
        if modified_at_iso:
            payload["properties"]["modifiedAt"] = modified_at_iso

        # Try create first (POST); if it already exists, update (PUT)
        try:
            self._post("/v1/objects", payload)
        except WeaviateError as e:
            # Duplicate/exists -> update instead
            print(f"Slide upsert POST failed, trying PUT: {e}")
            self._put(f"/v1/objects/{uid}", payload)
        return uid

    def upsert_images_and_link(
        self,
        *,
        course_id: str,
        document_id: str,
        slide_no: int,
        images: Iterable[Tuple[str, str]],
        image_description: str,
        text_vector: Sequence[float],
        created_at_iso: Optional[str] = None,
        modified_at_iso: Optional[str] = None,
        slide_uuid: Optional[str] = None,
    ) -> List[str]:
        """
        For each (image_base64, description):
        - create/replace a SlideImage object
        - add a reference from Slide.images -> that SlideImage
        Reference endpoint:
        POST /v1/objects/{fromClass}/{fromId}/references/{propName}
        body: {"beacon":"weaviate://localhost/{toClass}/{toId}"}
        """
        slide_id = slide_uuid or self._default_slide_uuid(document_id, slide_no)

        created_ids: List[str] = []
        for idx, (img_b64, desc) in enumerate(images, start=1):
            img_id = self._default_image_uuid(document_id, slide_no, idx)
            obj_payload = {
                "class": "SlideImage",
                "id": img_id,
                "properties": {
                    "courseId": course_id,
                    "documentId": document_id,
                    "slideNo": slide_no,
                    "imageBase64": img_b64,
                    "description": (desc or image_description or ""),
                },
                "vector": list(text_vector),
            }
            if created_at_iso:
                obj_payload["properties"]["createdAt"] = created_at_iso
            if modified_at_iso:
                obj_payload["properties"]["modifiedAt"] = modified_at_iso

            # Create (POST), or update (PUT) if it already exists
            try:
                self._post("/v1/objects", obj_payload)
            except WeaviateError as e:
                print(f"SlideImage upsert POST failed, trying PUT: {e}")
                self._put(f"/v1/objects/{img_id}", obj_payload)

            # Add reference from the slide to this image
            ref_body = {"beacon": f"weaviate://localhost/SlideImage/{img_id}"}
            self._post(f"/v1/objects/Slide/{slide_id}/references/images", ref_body)

            created_ids.append(img_id)

        return created_ids

    def upsert_video_chunk(
        self,
        *,
        course_id: str,
        lecture_id: str,
        chunk_id: str,
        text: str,
        text_vector: Sequence[float],
    ) -> str:
        """
        Create/replace a VideoChunk object with its text embedding (BYO vector).
        Uses POST to create; on conflict falls back to PUT to update (idempotent).
        :return: UUID used for the video chunk
        """
        # Generate deterministic UUID from course_id and chunk_id
        name = f"VideoChunk::{course_id}::{chunk_id}"
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, name))

        payload = {
            "class": "VideoChunk",
            "id": uid,
            "properties": {
                "courseId": course_id,
                "lectureId": lecture_id,
                "chunkId": chunk_id,
                "text": text,
            },
            "vector": list(text_vector),
        }

        # Try create first (POST); if it already exists, update (PUT)
        try:
            self._post("/v1/objects", payload)
        except WeaviateError as e:
            # Duplicate/exists -> update instead
            print(f"VideoChunk upsert POST failed, trying PUT: {e}")
            self._put(f"/v1/objects/{uid}", payload)
        return uid

    def test_upsert_video_chunk(self) -> str:
        to_upsert = 'A for loop is a control structure used to repeat a block of code a specific number of times. It is especially useful when you know in advance how many iterations you need. In most programming languages, a for loop consists of an initialization, a condition, and an update step. For example, it can be used to iterate over a range of numbers or through elements of a collection like a list. By using for loops, repetitive tasks can be written more concisely and clearly. This makes code easier to maintain and less error-prone compared to writing the same instructions multiple times.' # noqa: E501
        text_vector = get_embedding_service().embed_text(to_upsert)
        uid = self.upsert_video_chunk(course_id="W2", lecture_id="lecture456", chunk_id="chunk789", text=to_upsert, text_vector=text_vector)
        return uid

    def client_search_slides_fused_with_images(
        self,
        *,
        query_vector: Sequence[float],
        course_id: str,
        k: int = 5,
        similarity_threshold: float = 0.80,
    ) -> List[Dict[str, Any]]:
        """
        Simple implementation using weaviate client to search slides and their images.
        """
        print("[WeaviateClientSearch] Starting client_search_slides_fused_with_images")
        print("[WeaviateClientSearch] Parameters:")
        print(f"[WeaviateClientSearch]   - course_id: {course_id}")
        print(f"[WeaviateClientSearch]   - k: {k}")
        print(f"[WeaviateClientSearch]   - query_vector length: {len(query_vector) if query_vector else 'None'}")

        if not course_id:
            print("[WeaviateClientSearch] ERROR: course_id is empty or None")
            raise ValueError("course_id is required and cannot be None or empty")

        print("[WeaviateClientSearch] Getting weaviate client...")
        client = get_weaviate_client()
        print(f"[WeaviateClientSearch] Client obtained: {type(client)}")

        # Search slides using client
        print("[WeaviateClientSearch] Building slide query...")
        print(f"[WeaviateClientSearch] Query vector first 5 elements: {query_vector[:5] if len(query_vector) >= 5 else query_vector}")

        slides = client.collections.get("Slide")
        slideImages = client.collections.get("SlideImage")

        slide_query = slides.query.near_vector(
            near_vector=query_vector,  # your query vector goes here
            limit=k,
            certainty=similarity_threshold,
            return_metadata=MetadataQuery(distance=True, certainty=True),
            filters=Filter.by_property("courseId").equal(course_id),
        )

        slide_hits = slide_query.objects

        slide_hits_document_ids = [(s.properties["documentId"], s.properties["slideNo"]) for s in slide_hits]

        print(slide_hits_document_ids)

        if len(slide_hits_document_ids) == 0:
            print("[WeaviateClientSearch] No slide hits found, returning empty list")
            return []

        # Build filters for each (documentId, slideNo) pair
        slide_image_filters = [Filter.all_of([Filter.by_property("documentId").equal(doc_id), Filter.by_property("slideNo").equal(slide_no)]) for doc_id, slide_no in slide_hits_document_ids]
        slide_image_query = slideImages.query.fetch_objects(filters=Filter.any_of(slide_image_filters))

        slide_image_hits = slide_image_query.objects
        print(f"[WeaviateClientSearch] Retrieved {len(slide_image_hits)} slide images")
        for i, img in enumerate(slide_image_hits):
            print(f"[WeaviateClientSearch]   Image {i}: courseId={img.properties.get('courseId')}, slideNo={img.properties.get('slideNo')}, documentId={img.properties.get('documentId')}")
            print(f"[WeaviateClientSearch]     Description preview: {(img.properties.get('description', '') or '')[:100]}...")
            print(f"[WeaviateClientSearch]     ImageBase64 length: {len(img.properties.get('imageBase64', '') or '')}")

            # build output
        print("[WeaviateClientSearch] Building final results...")
        final_results = []

        # Group images by (documentId, slideNo)
        from collections import defaultdict

        images_by_slide = defaultdict(list)
        for img in slide_image_hits:
            key = (img.properties.get("documentId"), img.properties.get("slideNo"))
            images_by_slide[key].append({"description": img.properties.get("description", ""), "imageBase64": img.properties.get("imageBase64", "")})

        print(f"[WeaviateClientSearch] Grouped images by slide: {len(images_by_slide)} unique slides")

        # Build results for each slide hit
        for slide_idx, slide in enumerate(slide_hits):
            print(f"[WeaviateClientSearch] Processing slide {slide_idx + 1}/{len(slide_hits)}")

            slide_props = slide.properties
            slide_metadata = slide.metadata

            # Get images for this slide
            slide_key = (slide_props.get("documentId"), slide_props.get("slideNo"))
            slide_images = images_by_slide.get(slide_key, [])

            print(f"[WeaviateClientSearch] Slide {slide_idx}: courseId={slide_props.get('courseId')}, slideNo={slide_props.get('slideNo')}")
            print(f"[WeaviateClientSearch]   Distance: {slide_metadata.distance}, Certainty: {slide_metadata.certainty}")
            print(f"[WeaviateClientSearch]   Found {len(slide_images)} images for this slide")

            # Calculate similarity from distance
            result_slide = {
                "id": slide.uuid,
                "courseId": slide_props.get("courseId"),
                "documentId": slide_props.get("documentId"),
                "slideNo": slide_props.get("slideNo"),
                "slideDescription": slide_props.get("slideDescription", ""),
                "distance": slide_metadata.distance,
                "certainty": slide_metadata.certainty,
                "images": slide_images,
            }

            print(f"[WeaviateClientSearch] Slide confidence scores - Distance: {slide_metadata.distance},    Certainty: {slide_metadata.certainty}")
            print(f"[WeaviateClientSearch] Added slide {slide_props.get('slideNo')} with {len(slide_images)} images to results")

            final_results.append(result_slide)

        print("[WeaviateClientSearch] Completed processing all slides")
        print(f"[WeaviateClientSearch] Final results count: {len(final_results)}")
        print("[WeaviateClientSearch] Final results summary:")
        for i, result in enumerate(final_results):
            distance = result.get("distance")
            similarity = result.get("similarity")
            certainty = result.get("certainty")
            print(f"[WeaviateClientSearch]   Result {i}: courseId={result.get('courseId')}, slideNo={result.get('slideNo')}, images_count={len(result.get('images', []))}")
            print(f"[WeaviateClientSearch]   Confidence: distance={distance}, similarity={similarity}, certainty={certainty}")

        print(f"[WeaviateClientSearch] Returning {len(final_results)} results")
        return final_results

    def client_search_video_chunks(
        self,
        *,
        query_vector: Sequence[float],
        course_id: Optional[str] = None,
        k: int = 5,
        similarity_threshold: float = 0.80,
    ) -> List[Dict[str, Any]]:
        """
        Simple implementation using weaviate client to search video chunks.
"""
        print("[WeaviateClientSearch] Starting client_search_video_chunks")
        print("[WeaviateClientSearch] Parameters:")
        print(f"[WeaviateClientSearch]   - course_id: {course_id}")
        print(f"[WeaviateClientSearch]   - k: {k}")
        print(f"[WeaviateClientSearch]   - similarity_threshold: {similarity_threshold}")
        print(f"[WeaviateClientSearch]   - query_vector length: {len(query_vector) if query_vector else 'None'}")

        print("[WeaviateClientSearch] Getting weaviate client...")
        client = get_weaviate_client()
        print(f"[WeaviateClientSearch] Client obtained: {type(client)}")

        # Search video chunks using client
        print("[WeaviateClientSearch] Building video chunk query...")
        print(f"[WeaviateClientSearch] Query vector first 5 elements: {query_vector[:5] if len(query_vector) >= 5 else query_vector}")

        video_chunks = client.collections.get("VideoChunk")

        # Build the query with optional course filter
        if course_id:
            chunk_query = video_chunks.query.near_vector(
                near_vector=query_vector,
                limit=k,
                certainty=similarity_threshold,  # Using similarity_threshold as certainty
                return_metadata=MetadataQuery(distance=True, certainty=True),
                filters=Filter.by_property("courseId").equal(course_id),
            )
        else:
            chunk_query = video_chunks.query.near_vector(
                near_vector=query_vector,
                limit=k,
                certainty=similarity_threshold,
                return_metadata=MetadataQuery(distance=True, certainty=True),
            )

        chunk_hits = chunk_query.objects
        print(f"[WeaviateClientSearch] Found {len(chunk_hits)} video chunk hits")

        if len(chunk_hits) == 0:
            print("[WeaviateClientSearch] No video chunk hits found, returning empty list")
            return []

        # Build output
        print("[WeaviateClientSearch] Building final results...")
        final_results = []

        # Build results for each chunk hit
        for chunk_idx, chunk in enumerate(chunk_hits):
            print(f"[WeaviateClientSearch] Processing chunk {chunk_idx + 1}/{len(chunk_hits)}")

            chunk_props = chunk.properties
            chunk_metadata = chunk.metadata

            print(f"[WeaviateClientSearch] Chunk {chunk_idx}: courseId={chunk_props.get('courseId')}, chunkId={chunk_props.get('chunkId')}")
            print(f"[WeaviateClientSearch]   Distance: {chunk_metadata.distance}, Certainty: {chunk_metadata.certainty}")
            print(f"[WeaviateClientSearch]   Text preview: {(chunk_props.get('text', '') or '')[:100]}...")

            # Calculate similarity from distance using the existing method
            similarity = self._similarity_from_distance(chunk_metadata.distance)

            result_chunk = {
                "id": chunk.uuid,
                "courseId": chunk_props.get("courseId"),
                "lectureId": chunk_props.get("lectureId"),
                "chunkId": chunk_props.get("chunkId"),
                "text": chunk_props.get("text", ""),
                "distance": chunk_metadata.distance,
                "certainty": chunk_metadata.certainty,
                "similarity": similarity,
            }

            print(f"[WeaviateClientSearch] Chunk confidence scores - Distance: {chunk_metadata.distance}, Certainty: {chunk_metadata.certainty}, Similarity: {similarity}")
            print(f"[WeaviateClientSearch] Added chunk {chunk_props.get('chunkId')} to results")

            final_results.append(result_chunk)

        print("[WeaviateClientSearch] Completed processing all chunks")
        print(f"[WeaviateClientSearch] Final results count: {len(final_results)}")
        print("[WeaviateClientSearch] Final results summary:")
        for i, result in enumerate(final_results):
            distance = result.get("distance")
            similarity = result.get("similarity")
            certainty = result.get("certainty")
            print(f"[WeaviateClientSearch]   Result {i}: courseId={result.get('courseId')}, chunkId={result.get('chunkId')}")
            print(f"[WeaviateClientSearch]   Confidence: distance={distance}, similarity={similarity}, certainty={certainty}")

        print(f"[WeaviateClientSearch] Returning {len(final_results)} results")
        return final_results

    def client_get_both_slides_and_video_chunks(
        self,
        *,
        query_vector: Sequence[float],
        course_id: Optional[str] = None,
        k: int = 5,
        similarity_threshold: float = 0.80
    ) -> Dict[str, Any]:
        slide_hits = self.client_search_slides_fused_with_images(
            query_vector=query_vector,
            course_id=course_id,
            k=k,
            similarity_threshold=similarity_threshold
        )

        video_chunk_hits = self.client_search_video_chunks(
            query_vector=query_vector,
            course_id=course_id,
            k=k,
            similarity_threshold=similarity_threshold
        )

        print(f"Retrieved {len(slide_hits)} hits from store")

        # Convert to OpenAPI format
        response: Dict[str, Any] = self.to_retrieval_response(slide_hits, video_chunk_hits)
        return response

    # Test/Debug functions
    def get_all_data_for_course(self, course_id: str) -> Dict[str, Any]:
        """
        Test function: Get all slides and images for a courseId (no vector search).
        Returns all data for debugging purposes.
        """
        # Get all slides for the course
        gql_slides = f"""
        {{
          Get {{
            Slide(
              where: {{ operator: Equal, path: ["courseId"], valueText: "{course_id}" }}
              limit: 100
            ) {{
              courseId
              documentId
              slideNo
              slideDescription
              _additional {{ id }}
            }}
          }}
        }}
        """
        res_slides = self._post("/v1/graphql", {"query": gql_slides})
        slides = res_slides.get("data", {}).get("Get", {}).get("Slide", []) or []

        # Get all images for the course
        gql_images = f"""
        {{
          Get {{
            SlideImage(
              where: {{ operator: Equal, path: ["courseId"], valueText: "{course_id}" }}
              limit: 500
            ) {{
              courseId
              documentId
              slideNo
              description
              imageBase64
              _additional {{ id }}
            }}
          }}
        }}
        """
        res_images = self._post("/v1/graphql", {"query": gql_images})
        images = res_images.get("data", {}).get("Get", {}).get("SlideImage", []) or []

        return {"courseId": course_id, "totalSlides": len(slides), "totalImages": len(images), "slides": slides, "images": images}

    # Mapping to OpenAPI response shape
    @staticmethod
    def to_retrieval_response(
        slide_hits: List[Dict[str, Any]] = None,
        video_chunk_hits: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert slide hits and video chunk hits into your OpenAPI RetrievalResponse:
        {
            "content": ["string", ...],
            "images": [{"image":"<base64>", "description":"..."}, ...]
        }

        Strategy:
        - Merge slides and video chunks based on certainty scores (highest first)
        - For content[], include slideDescription from slides and text from video chunks
        - For images[], attach all images from slide hits only
        - Items are ordered by certainty score descending
        """
        content: List[str] = []
        images: List[Dict[str, str]] = []

        # Normalize inputs
        slide_hits = slide_hits or []
        video_chunk_hits = video_chunk_hits or []

        # Create combined list with type indicator and certainty score
        combined_items = []

        # Add slides to combined list
        for slide in slide_hits:
            certainty = slide.get("certainty", 0.0)
            combined_items.append({
                "type": "slide",
                "certainty": certainty,
                "item": slide
            })

        # Add video chunks to combined list
        for chunk in video_chunk_hits:
            certainty = chunk.get("certainty", 0.0)
            combined_items.append({
                "type": "video_chunk",
                "certainty": certainty,
                "item": chunk
            })

        # Sort combined items by certainty score (highest first)
        combined_items.sort(key=lambda x: x["certainty"], reverse=True)

        # Process items in order of certainty
        for item in combined_items:
            if item["type"] == "slide":
                slide = item["item"]
                desc = (slide.get("slideDescription") or "").strip()
                if desc:
                    content.append(desc)

                # Collect images from slides
                for im in slide.get("images", []):
                    img_b64 = im.get("imageBase64")
                    if img_b64:
                        images.append({
                            "image": img_b64,
                            "description": im.get("description") or "",
                        })

            elif item["type"] == "video_chunk":
                chunk = item["item"]
                text = (chunk.get("text") or "").strip()
                if text:
                    content.append(text)

        return {"content": content, "images": images}


_weaviate_instance: Optional[weaviate.WeaviateClient] = None


def get_weaviate_client() -> weaviate.WeaviateClient:
    global _weaviate_instance

    if _weaviate_instance is None:
        _weaviate_instance = weaviate.connect_to_local(host="docint-weaviate", port=28947)

    if _weaviate_instance.is_connected() is False:
        print("[WeaviateClient] WARNING: Weaviate client is not connected!")
        # Optionally, raise an error or attempt reconnection here.
        _weaviate_instance = weaviate.connect_to_local(host="docint-weaviate", port=28947)
    return _weaviate_instance

_store_instance: Optional[WeaviateGraphStore] = None

def get_store() -> WeaviateGraphStore:
    global _store_instance

    if _store_instance is None:
        _store_instance = WeaviateGraphStore()

    return _store_instance