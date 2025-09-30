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

- Key ops:
  * ensure_schema()               -> idempotent schema creation + reference property
  * upsert_slide(...)             -> create/replace Slide with text vector
  * upsert_images_and_link(...)   -> create SlideImage objects + link to Slide.images
  * search_slides_with_images(...) -> single GraphQL query: ANN + traverse images
  * to_retrieval_response(...)    -> map hits -> OpenAPI RetrievalResponse

Notes:
- BYO embeddings: send your text vector when upserting Slide.
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
from weaviate.connect import ConnectionParams


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
        except WeaviateError:
            # Duplicate/exists -> update instead
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
            except WeaviateError:
                self._put(f"/v1/objects/{img_id}", obj_payload)

            # Add reference from the slide to this image
            ref_body = {"beacon": f"weaviate://localhost/SlideImage/{img_id}"}
            self._post(f"/v1/objects/Slide/{slide_id}/references/images", ref_body)

            created_ids.append(img_id)

        return created_ids

    # Query (dual-channel with fusion: text on Slide + image-description on SlideImage)
    def search_slides_fused_with_images(
        self,
        *,
        query_vector: Sequence[float],
        course_id: Optional[str] = None,
        k: int = 5,
        image_query_vector: Optional[Sequence[float]] = None,
        alpha: float = 0.8,  # Default weight for text is now 70%
        similarity_threshold: float = 0.70,  # Results must meet this score
        per_slide_image_agg: str = "max",  # How to aggregate image scores per slide
        include_distance: bool = True,  # Whether to include distance information
    ) -> List[Dict[str, Any]]:
        """
        Retrieves slides by fusing text and image similarity scores without normalization.
          1. Perform separate searches for relevant slides (text) and images.
          2. Calculating an absolute fused score for each unique slide found.
          3. Filtering out any slides that do not meet the `similarity_threshold`.
          4. Ranking the remaining relevant slides and returning the top-k.
        """
        print(f"[DEBUG] search_slides_fused_with_images called with:")
        print(f"  - course_id: {course_id}")
        print(f"  - k: {k}")
        print(f"  - alpha: {alpha}")
        print(f"  - similarity_threshold: {similarity_threshold}")
        print(f"  - per_slide_image_agg: {per_slide_image_agg}")
        print(f"  - query_vector length: {len(query_vector) if query_vector else 'None'}")
        print(f"  - image_query_vector length: {len(image_query_vector) if image_query_vector else 'None'}")

        # Text ANN on Slide
        where_clause = ""
        if course_id:
            where_clause = f'where: {{ operator: Equal, path: ["courseId"], valueText: "{course_id}" }}'
        print(f"[DEBUG] where_clause: {where_clause}")

        gql_slides = f"""
        {{
          Get {{
            Slide(
              nearVector: {{ vector: {json.dumps(list(query_vector))} }}
              {where_clause}
              limit: {int(max(k * 5, 50))}
            ) {{
              courseId, documentId, slideNo, slideDescription,
              _additional {{ id, distance }}
            }}
          }}
        }}
        """
        print(f"[DEBUG] GraphQL query for slides:")
        print(gql_slides)

        res_slides = self._post("/v1/graphql", {"query": gql_slides})
        print(f"[DEBUG] Raw slide search response: {res_slides}")

        slide_hits = res_slides.get("data", {}).get("Get", {}).get("Slide", []) or []
        print(f"[DEBUG] Found {len(slide_hits)} slide hits")
        for i, hit in enumerate(slide_hits):
            print(f"  Slide {i}: courseId={hit.get('courseId')}, slideNo={hit.get('slideNo')}, distance={hit.get('_additional', {}).get('distance')}")

        text_scores: Dict[tuple, float] = {}
        slide_meta: Dict[tuple, Dict[str, Any]] = {}
        for s in slide_hits:
            key = (s.get("courseId"), s.get("slideNo"))
            dist = (s.get("_additional") or {}).get("distance")
            text_scores[key] = self._similarity_from_distance(dist)
            slide_meta[key] = s

        print(f"[DEBUG] Text scores computed: {text_scores}")
        print(f"[DEBUG] Slide metadata keys: {list(slide_meta.keys())}")

        # Image-description ANN on SlideImage
        img_vec = image_query_vector if image_query_vector is not None else query_vector
        print(f"[DEBUG] Using image vector - is separate: {image_query_vector is not None}")

        gql_images = f"""
        {{
          Get {{
            SlideImage(
              nearVector: {{ vector: {json.dumps(list(img_vec))} }}
              {where_clause}
              limit: {int(max(k * 10, 100))}
            ) {{
              courseId, documentId, slideNo,
              _additional {{ id, distance }}
            }}
          }}
        }}
        """
        print(f"[DEBUG] GraphQL query for images:")
        print(gql_images)

        res_images = self._post("/v1/graphql", {"query": gql_images})
        print(f"[DEBUG] Raw image search response: {res_images}")

        img_hits = res_images.get("data", {}).get("Get", {}).get("SlideImage", []) or []
        print(f"[DEBUG] Found {len(img_hits)} image hits")
        for i, hit in enumerate(img_hits):
            print(f"  Image {i}: courseId={hit.get('courseId')}, slideNo={hit.get('slideNo')}, distance={hit.get('_additional', {}).get('distance')}")

        from collections import defaultdict

        per_slide_image_sims: Dict[tuple, List[float]] = defaultdict(list)
        for im in img_hits:
            key = (im.get("courseId"), im.get("slideNo"))
            dist = (im.get("_additional") or {}).get("distance")
            sim_score = self._similarity_from_distance(dist)
            per_slide_image_sims[key].append(sim_score)
            print(f"[DEBUG] Image similarity for slide {key}: distance={dist}, similarity={sim_score}")

        print(f"[DEBUG] Per-slide image similarities: {dict(per_slide_image_sims)}")

        # Aggregate image scores per slide using the specified method
        image_scores: Dict[tuple, float] = {}
        for key, vals in per_slide_image_sims.items():
            if vals:
                if per_slide_image_agg == "mean":
                    image_scores[key] = sum(vals) / len(vals)
                else:  # default to "max"
                    image_scores[key] = max(vals)
                print(f"[DEBUG] Aggregated image score for slide {key}: {image_scores[key]} (method: {per_slide_image_agg})")

        print(f"[DEBUG] Final image scores: {image_scores}")

        # Fuse scores without normalization
        fused_scores: Dict[tuple, float] = {}
        all_slide_keys = set(text_scores.keys()) | set(image_scores.keys())
        print(f"[DEBUG] All unique slide keys found: {all_slide_keys}")
        print(f"[DEBUG] Text score keys: {set(text_scores.keys())}")
        print(f"[DEBUG] Image score keys: {set(image_scores.keys())}")

        for key in all_slide_keys:
            text_sim = text_scores.get(key, 0.0)
            image_sim = image_scores.get(key, 0.0)

            # Direct weighted sum
            fused_score = (alpha * text_sim) + ((1.0 - alpha) * image_sim)
            fused_scores[key] = fused_score
            print(f"[DEBUG] Fused score for slide {key}: text={text_sim}, image={image_sim}, fused={fused_score}")

        print(f"[DEBUG] All fused scores: {fused_scores}")

        # Filter by threshold, then sort and limit
        # Only keep slides that meet the similarity threshold
        relevant_slides = {key: score for key, score in fused_scores.items() if score >= similarity_threshold}
        print(f"[DEBUG] Slides meeting threshold {similarity_threshold}: {relevant_slides}")
        print(f"[DEBUG] Filtered out {len(fused_scores) - len(relevant_slides)} slides below threshold")

        # Sort the relevant slides by their fused score, descending
        sorted_slides = sorted(relevant_slides.items(), key=lambda item: item[1], reverse=True)
        print(f"[DEBUG] Sorted relevant slides: {sorted_slides}")

        # Get the keys for the top k slides
        top_keys = [key for key, score in sorted_slides[:k]]
        print(f"[DEBUG] Top {k} slide keys selected: {top_keys}")

        # Assemble final results
        out: List[Dict[str, Any]] = []
        print(f"[DEBUG] Starting to assemble final results for {len(top_keys)} slides")

        for i, key in enumerate(top_keys):
            c_id, s_no = key
            print(f"[DEBUG] Processing slide {i + 1}/{len(top_keys)}: {key}")

            # Get metadata for the slide, falling back to a direct fetch if it wasn't in the initial text search
            s_meta = slide_meta.get(key)
            if not s_meta:
                print(f"[DEBUG] Slide metadata not found in cache, fetching directly for {key}")
                # This fallback is for slides that were found only through an image match
                gql_one = f"""
                {{
                    Get {{
                    Slide(
                        where: {{
                        operator: And,
                        operands: [
                            {{ operator: Equal, path: ["courseId"], valueText: "{c_id}" }},
                            {{ operator: Equal, path: ["slideNo"],  valueInt: {int(s_no)} }}
                        ]
                        }},
                        limit: 1
                    ) {{
                        courseId, documentId, slideNo, slideDescription,
                        _additional {{ id }}
                    }}
                    }}
                }}
                """
                res_one = self._post("/v1/graphql", {"query": gql_one})
                print(f"[DEBUG] Direct fetch response for slide {key}: {res_one}")
                recs = res_one.get("data", {}).get("Get", {}).get("Slide", []) or []
                s_meta = recs[0] if recs else {}
                print(f"[DEBUG] Retrieved slide metadata: {s_meta}")
            else:
                print(f"[DEBUG] Using cached slide metadata for {key}")

            # Fetch all images for the final slide
            print(f"[DEBUG] Fetching images for slide {key}")
            images_full = self._fetch_all_images_for_slide(c_id, s_no)
            print(f"[DEBUG] Found {len(images_full)} images for slide {key}")

            # Correctly retrieve the calculated scores from the dictionaries
            final_fused_score = fused_scores.get(key, 0.0)
            final_text_sim = text_scores.get(key, 0.0)
            final_image_sim = image_scores.get(key, 0.0)
            text_dist = (slide_meta.get(key, {}).get("_additional") or {}).get("distance") if key in slide_meta else None

            print(f"[DEBUG] Final scores for slide {key}:")
            print(f"  - fused: {final_fused_score}")
            print(f"  - text similarity: {final_text_sim}")
            print(f"  - image similarity: {final_image_sim}")
            print(f"  - text distance: {text_dist}")

            result_slide = {
                "id": (s_meta.get("_additional") or {}).get("id"),
                "courseId": c_id,
                "documentId": s_meta.get("documentId"),
                "slideNo": s_no,
                "slideDescription": s_meta.get("slideDescription", ""),
                # Flatten scores to top level for RetrievalService compatibility
                "fusedScore": final_fused_score,
                "similarityText": final_text_sim,
                "bestImageSimilarity": final_image_sim,
                "distanceText": text_dist,
                "images": [{"id": (im.get("_additional") or {}).get("id"), "description": im.get("description", ""), "imageBase64": im.get("imageBase64")} for im in images_full],
            }
            print(f"[DEBUG] Adding slide result {i + 1}: {result_slide['courseId']}/{result_slide['slideNo']}")
            out.append(result_slide)

        print(f"[DEBUG] Final search results: {len(out)} slides returned")
        return out

    def client_search_slides_fused_with_images(
        self,
        *,
        query_vector: Sequence[float],
        course_id: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Simple implementation using weaviate client to search slides and their images.
        """
        print(f"[WeaviateClientSearch] Starting client_search_slides_fused_with_images")
        print(f"[WeaviateClientSearch] Parameters:")
        print(f"[WeaviateClientSearch]   - course_id: {course_id}")
        print(f"[WeaviateClientSearch]   - k: {k}")
        print(f"[WeaviateClientSearch]   - query_vector length: {len(query_vector) if query_vector else 'None'}")

        if not course_id:
            print(f"[WeaviateClientSearch] ERROR: course_id is empty or None")
            raise ValueError("course_id is required and cannot be None or empty")

        print(f"[WeaviateClientSearch] Getting weaviate client...")
        client = get_weaviate_client()
        print(f"[WeaviateClientSearch] Client obtained: {type(client)}")

        # Search slides using client
        print(f"[WeaviateClientSearch] Building slide query...")
        print(f"[WeaviateClientSearch] Query vector first 5 elements: {query_vector[:5] if len(query_vector) >= 5 else query_vector}")

        slides = client.collections.get("Slide")
        slideImages = client.collections.get("SlideImage")

        slide_query = slides.query.near_vector(
            near_vector=query_vector,  # your query vector goes here
            limit=k,
            certainty=0.8,
            return_metadata=MetadataQuery(distance=True, certainty=True),
            filters=Filter.by_property("courseId").equal(course_id),
        )

        slide_hits = slide_query.objects

        slide_hits_document_ids = [(s.properties["documentId"], s.properties["slideNo"]) for s in slide_hits]

        print(slide_hits_document_ids)

        if len(slide_hits_document_ids) == 0:
            print(f"[WeaviateClientSearch] No slide hits found, returning empty list")
            return []

        slide_image_query = slideImages.query.fetch_objects(filters=Filter.any_of([Filter.all_of([Filter.by_property("documentId").equal(doc_id), Filter.by_property("slideNo").equal(slide_no)]) for doc_id, slide_no in slide_hits_document_ids]))

        slide_image_hits = slide_image_query.objects
        print(f"[WeaviateClientSearch] Retrieved {len(slide_image_hits)} slide images")
        for i, img in enumerate(slide_image_hits):
            print(f"[WeaviateClientSearch]   Image {i}: courseId={img.properties.get('courseId')}, slideNo={img.properties.get('slideNo')}, documentId={img.properties.get('documentId')}")
            print(f"[WeaviateClientSearch]     Description preview: {(img.properties.get('description', '') or '')[:100]}...")
            print(f"[WeaviateClientSearch]     ImageBase64 length: {len(img.properties.get('imageBase64', '') or '')}")

            # build output
        print(f"[WeaviateClientSearch] Building final results...")
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

        print(f"[WeaviateClientSearch] Completed processing all slides")
        print(f"[WeaviateClientSearch] Final results count: {len(final_results)}")
        print(f"[WeaviateClientSearch] Final results summary:")
        for i, result in enumerate(final_results):
            distance = result.get("distance")
            similarity = result.get("similarity")
            certainty = result.get("certainty")
            print(f"[WeaviateClientSearch]   Result {i}: courseId={result.get('courseId')}, slideNo={result.get('slideNo')}, images_count={len(result.get('images', []))}")
            print(f"[WeaviateClientSearch]   Confidence: distance={distance}, similarity={similarity}, certainty={certainty}")

        print(f"[WeaviateClientSearch] Returning {len(final_results)} results")
        return final_results

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
    def to_retrieval_response(slide_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert hits into your OpenAPI RetrievalResponse:
          {
            "content": ["string", ...],
            "images": [{"image":"<base64>", "description":"..."}, ...]
          }

        Strategy:
          - For content[], we include title + body (+ captionsText if present) concisely.
          - For images[], we attach all images from the top hits.
        """
        content: List[str] = []
        images: List[Dict[str, str]] = []

        for h in slide_hits:
            desc = (h.get("slideDescription") or "").strip()
            if desc:
                content.append(desc)

            for im in h.get("images", []):
                img_b64 = im.get("imageBase64")
                if img_b64:
                    images.append(
                        {
                            "image": img_b64,
                            "description": im.get("description") or "",
                        }
                    )

        return {"content": content, "images": images}


_weaviate_instance: Optional[weaviate.WeaviateClient] = None


def get_weaviate_client() -> weaviate.WeaviateClient:
    global _weaviate_instance

    if _weaviate_instance is None:
        _weaviate_instance = weaviate.connect_to_local(host="docint-weaviate", port=28947)

    if _weaviate_instance.is_connected() is False:
        print("[WeaviateClient] WARNING: Weaviate client is not connected!")
        # Optionally, raise an error or attempt reconnection here.
        _weaviate_instance = weaviate.connect_to_local(host="docint-weaviate", port=50051)
    return _weaviate_instance
