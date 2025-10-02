"""
Python script: Refine lecture content based on student persona

This script takes:
1. Retrieved content from RAG for sub-questions
2. A student's persona

It produces a single lecture script with image references.
Output format:
{
  "lectureScript": "...",
  "Images": [{"image": "...", "description": "..."}]
}
"""

import json
import re
import os

# -----------------------------
# JSON helpers
# -----------------------------
from typing import Any, List, Tuple

from pydantic import BaseModel, Field

from service_core.models.slides.request_slide_generation_request_assets_inner import (
    RequestSlideGenerationRequestAssetsInner,
)
from service_core.models.user_profile import UserProfile
from service_core.models.docint.retrieval_response import (
    RetrievalResponse as DocintRetrievalResponse,
)
from service_core.services.helpers.handle_retrieved import (
    map_docint_file_to_slides_asset,
    ContentWithAssets,
)
from service_core.services.helpers.llm import ask_llm


def try_parse_json(raw_response: str) -> Tuple[bool, Any]:
    """Try to parse JSON response, return (success, result)"""
    try:
        result = json.loads(raw_response)
        return True, result
    except json.JSONDecodeError:
        return False, None


# -----------------------------
# Refine lecture content
# -----------------------------


class ReducedAsset(BaseModel):
    name: str
    asset_description: str = Field(alias="assetDescription")


class LectureScriptWithReducedAssets(BaseModel):
    lecture_script: str = Field(default="", alias="lectureScript")
    assets: List[ReducedAsset] = Field(default=[])


class LectureScriptWithAssets(BaseModel):
    lecture_script: str = Field(default="", alias="lectureScript")
    assets: List[RequestSlideGenerationRequestAssetsInner] = Field(default=[])


def generate_script_llm(
    retrieved_content: List[ContentWithAssets], persona: Any
) -> LectureScriptWithReducedAssets:
    if hasattr(persona, "dict"):
        persona_dict = persona.dict()
    elif hasattr(persona, "model_dump"):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona

    persona_dict["id"] = str(persona_dict["id"])

    persona_str = json.dumps(persona_dict, indent=2, ensure_ascii=False)
    content_str = json.dumps(
        list(
            map(
                lambda content_with_assets: content_with_assets.build_desc_map(),
                retrieved_content,
            )
        ),
        indent=2,
        ensure_ascii=False,
    )
    prompt = f"""
        You are an expert AI assistant specializing in personalized educational content creation. Your purpose is to transform raw educational material into an engaging and effective lecture script tailored to a specific learner's profile.\n\n
        Your task is to synthesize the provided content into a single, coherent lecture script.
        This script must be meticulously tailored to the specified learner PERSONA.\n\n
        ---\n### INPUTS\n---\n\n1. PERSONA: A JSON object describing the target student.
            \njson\n{persona_str}\n\n\n
        2. RETRIEVED_CONTENT: A string of text containing the raw information for the lecture.\n\n{content_str}\n\n\n
        ---\n### RULES & GUIDELINES\n---\n\n
        * Persona-Driven Adaptation: You MUST adapt the script based on the PERSONA object:\n
        * Tone & Style: Match the persona's preferred communication style (e.g., formal, conversational, enthusiastic, humorous).\n
        * Complexity & Depth: Adjust the technical jargon, depth of explanation, and complexity of concepts to the persona's knowledgeLevel (e.g., "Beginner", "Intermediate", "Expert").\n
        * Examples & Analogies: Generate relevant and relatable examples, analogies, or case studies that align with the persona's interests and goals.\n
        * Language: The entire lecture script MUST be written in the language specified in the persona's language field.\n\n
        * Image Integration: Strategically identify points in the lecture where a given image would significantly enhance understanding.\n
        * In the lectureScript, reference the image with the filename (e.g., [Here you can see filename_1.jpg])\n
        * For each referenced image, add a corresponding object to the Images list in the final JSON output.\n
        * Image filenames need to match the given namens.\n\n
        * Coherence: The final lectureScript must flow logically and be structured as a single, cohesive piece, not a list of disconnected facts.\n\n
        ---\n### OUTPUT FORMAT\n---\n\n
        Your response MUST be a single, valid JSON object and nothing else. Do not include any introductory text, explanations, or markdown formatting (like json) around the JSON object.
        The property names need to be enclosed in double quotes. The JSON object must strictly adhere to the following structure:\n\njson\n{{
    "lectureScript": "A single string containing the entire lecture script. Use \\n for new paragraphs and \\t for indentation if needed.",
    "assets": [
        {{
        "name": "filename_1.jpg",
        "assetDescription": "A concise and clear description of the content and purpose of the first image."
        }},
        {{
        "name": "filename_2.png",
        "assetDescription": "A description for the second image."
        }}
    ]
    }}
    """
    max_retries = 3

    def extract_json(text: str) -> str:
        # Remove code block markers and stray text
        text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
        # Find first { ... } block
        match = re.search(r"{.*?}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    for attempt in range(max_retries):
        try:
            raw_message = ask_llm(prompt)
            raw: str = str(raw_message)
            success, result = try_parse_json(raw)

            if not success:
                # Try to extract JSON from messy output
                cleaned: str = extract_json(raw)
                success, result = try_parse_json(cleaned)
            if success:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return LectureScriptWithReducedAssets(**result)

            # If it didn't work, log the raw output for debugging
            log_dir = os.getenv("LLM_FAILED_LOG_DIR", os.path.join(os.getcwd(), "logs", "llm_failed_outputs"))
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"failed_output_attempt_{attempt+1}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(raw)

            # Explicitly raise JSONDecodeError to trigger retry, include attempt number
            raise json.JSONDecodeError(
                f"Failed to parse JSON on attempt {attempt+1}", raw, 0
            )

        except json.JSONDecodeError as e:
            print(f"JSON parsing error on attempt {attempt + 1}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to get valid response from LLM after {max_retries} attempts: {e}"
                )
            continue
    raise RuntimeError("LLM did not produce valid JSON response")


def generate_script(
    content: List[DocintRetrievalResponse], persona: UserProfile
) -> LectureScriptWithAssets:
    retrieved_content: List[ContentWithAssets] = map_docint_file_to_slides_asset(
        content
    )
    asset_lookup = {
        asset.name: asset for content in retrieved_content for asset in content.assets
    }

    generated_script_with_assets = generate_script_llm(retrieved_content, persona)
    return LectureScriptWithAssets(
        lectureScript=generated_script_with_assets.lecture_script,
        assets=[
            asset_lookup[red_asset.name]
            for red_asset in generated_script_with_assets.assets
            if red_asset.name in asset_lookup
        ],
    )