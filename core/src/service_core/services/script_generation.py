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
from service_core.services.helpers.llm import getLLM  
import json
from typing import Dict, Any, List
from service_core.services.helpers.handle_retrieved import convert_json_structure
import copy
from service_core.models.user_profile import UserProfile
# -----------------------------
# JSON helpers
# -----------------------------
def try_parse_json(raw_response: str):
    """Try to parse JSON response, return (success, result)"""
    try:
        result = json.loads(raw_response)
        return True, result
    except json.JSONDecodeError:
        return False, None


# -----------------------------
# Refine lecture content
# -----------------------------

def generate_script_llm(retrieved_content: List[Dict[str, Any]], persona):
    if hasattr(persona, 'dict'):
        persona_dict = persona.dict()
    elif hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona

    persona_dict['id'] = str(persona_dict['id'])

    #print("Refining lecture content for persona:")
    persona_str = json.dumps(persona_dict, indent=2, ensure_ascii=False)
    print(persona_str)
    content_str = json.dumps(retrieved_content, indent=2, ensure_ascii=False)
    print(content_str)
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
        Your response MUST be a single, valid JSON object and nothing else. Do not include any introductory text, explanations, or markdown formatting (like json) around the JSON object. The property names need to be enclosed in double quotes. The JSON object must strictly adhere to the following structure:\n\njson\n{{
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
    print(prompt)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            raw_message = getLLM().invoke(prompt)
            raw = raw_message.content
            #print(f"\nBreak point (attempt {attempt + 1}): {raw}")

            
            # Clean the response: remove markdown and trim whitespace
            if '```json' in raw:
                raw = raw.split('```json')[1].split('```')[0]
            elif '```' in raw:
                raw = raw.split('```')[1].split('```')[0]
            
            raw = raw.strip()

            # Try to parse JSON
            success, result = try_parse_json(raw)
            if success:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            
            # If it didn't work, this will raise JSONDecodeError and trigger retry
            # This is useful for debugging the raw output on failure.
            json.loads(raw)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error on attempt {attempt + 1}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to get valid response from LLM after {max_retries} attempts: {e}")
            continue

def generate_script(retrieved_content: List[Dict[str, Any]], persona: UserProfile):
    
    retrieved_content = convert_json_structure(retrieved_content)
    
    # Create a lookup table for assets and a version of the content for the LLM
    asset_lookup = {}
    retrieved_content_for_llm = copy.deepcopy(retrieved_content)
    for item in retrieved_content_for_llm:
        # print('a', flush=True)
        if 'assets' in item:
            # print('b', flush=True)
            for asset in item['assets']:
                # print('c', flush=True)
                if 'name' in asset:
                    # Store the original asset data
                    asset_lookup[asset['name']] = {
                        'mimeType': asset.get('mimeType'),
                        'data': asset.get('data')
                    }
                # Remove bulky data for the LLM call
                asset.pop('mimeType', None)
                asset.pop('data', None)

    generated_script = generate_script_llm(retrieved_content_for_llm, persona)   
    print("\n\nGenerate Script Output:", generated_script)
    
    # Add mimetype and data back to the assets in the generated script
    assets = generated_script.get('assets', [])
    if assets:
        for asset in assets:
            print("asset:", asset)
            if 'name' in asset and asset['name'] in asset_lookup:
                asset.update(asset_lookup[asset['name']])
    print("\n\nFinal Generated Script with Assets:", json.dumps(generated_script, indent=2))
    return generated_script