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
from helpers.llm import getLLM  
import json
import textwrap
from typing import Dict, Any, List

# -----------------------------
# JSON helpers
# -----------------------------
def try_parse_json(raw_response: str) -> tuple[bool, dict]:
    """Try to parse JSON response, return (success, result)"""
    try:
        result = json.loads(raw_response)
        return True, result
    except json.JSONDecodeError:
        return False, None


# -----------------------------
# Refine lecture content
# -----------------------------
REFINE_PROMPT = textwrap.dedent("""
You are an expert AI assistant specializing in personalized educational content creation. Your purpose is to transform raw educational material into an engaging and effective lecture script tailored to a specific learner's profile.\n\n
Your task is to synthesize the provided content into a single, coherent lecture script.
This script must be meticulously tailored to the specified learner PERSONA.\n\n
---\n### INPUTS\n---\n\n1. PERSONA: A JSON object describing the target student.
    \njson\n{{persona_dict}}\n\n\n
2. RETRIEVED_CONTENT: A string of text containing the raw information for the lecture.\n\n{{retrieved_content}}\n\n\n
---\n### RULES & GUIDELINES\n---\n\n
* Persona-Driven Adaptation: You MUST adapt the script based on the PERSONA object:\n
* Tone & Style: Match the persona's preferred communication style (e.g., formal, conversational, enthusiastic, humorous).\n
* Complexity & Depth: Adjust the technical jargon, depth of explanation, and complexity of concepts to the persona's knowledgeLevel (e.g., "Beginner", "Intermediate", "Expert").\n
* Examples & Analogies: Generate relevant and relatable examples, analogies, or case studies that align with the persona's interests and goals.\n
* Language: The entire lecture script MUST be written in the language specified in the persona's language field.\n\n
* Image Integration: Strategically identify points in the lecture where a given image would significantly enhance understanding.\n
* In the lectureScript, reference the image with a clear placeholder (e.g., Here you can see a diagram showing the Krebs cycle]).\n
* For each referenced image, add a corresponding object to the Images list in the final JSON output.\n
* Image filenames need to match the given namens.\n\n
* Coherence: The final lectureScript must flow logically and be structured as a single, cohesive piece, not a list of disconnected facts.\n\n
---\n### OUTPUT FORMAT\n---\n\n
Your response MUST be a single, valid JSON object and nothing else. Do not include any introductory text, explanations, or markdown formatting (like json) around the JSON object. The JSON object must strictly adhere to the following structure:\n\njson\n{\n  "lectureScript": "A single string containing the entire lecture script. Use \n for new paragraphs and \t for indentation if needed.",\n  "Images": [\n    {\n      "image": "filename_1.jpg",\n      "description": "A concise and clear description of the content and purpose of the first image."\n    },\n    {\n      "image": "filename_2.png",\n      "description": "A description for the second image."\n    }\n  ]\n}\n```
""")

def generate_script(retrieved_content: List[Dict[str, Any]], persona: Dict[str, Any]) -> Dict[str, Any]:
    if hasattr(persona, 'dict'):
        persona_dict = persona.dict()
    elif hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona

    persona_dict['id'] = str(persona_dict['id'])
    print("Refining lecture content for persona:")

    prompt = REFINE_PROMPT + "\n\n" + json.dumps({
        "persona": persona_dict,
        "retrieved_content": retrieved_content
    }, ensure_ascii=False)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = getLLM().invoke(prompt)
            raw = response.content if hasattr(response, 'content') else str(response)
            print(f"\nBreak point (attempt {attempt + 1}): {raw}")

            # Clean the response: remove markdown fences and surrounding whitespace
            if '```json' in raw:
                raw = raw.split('```json', 1)[1]
            if '```' in raw:
                raw = raw.rsplit('```', 1)[0]
            raw = raw.strip()
            
            # Try to parse JSON
            success, result = try_parse_json(raw)
            if success:
                return result
            
            # If it didn't work, this will raise JSONDecodeError and trigger retry
            json.loads(raw)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error on attempt {attempt + 1}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to get valid response from LLM after {max_retries} attempts: {e}")
            continue

