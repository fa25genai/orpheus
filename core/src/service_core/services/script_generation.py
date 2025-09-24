# ░▒▓██████▓▒░░▒▓█▓▒░       ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░ 
#░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
#░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
#░▒▓████████▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓██████▓▒░   
#░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
#░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
#░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░       ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░ 
import json
import textwrap
from typing import Dict, Any, List
from helpers.llm import getLLM
from helpers.debug import enable_debug, debug_print
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
enable_debug()
# 1. Define the desired JSON output structure using Pydantic
class Lecture(BaseModel):
    """The generated lecture script and associated images."""
    lectureScript: str = Field(description="The full, coherent lecture script.")
    Images: List[Dict[str, str]] = Field(description='A list of images, each with a source and description. Example: [{"image": "url/to/image.jpg", "description": "a cat"}]')

# 2. Define a clear, structured prompt template
prompt_template = ChatPromptTemplate.from_template_file("prompts/script.json")
debug_print("Prompt Template Loaded:")
debug_print(textwrap.indent(prompt_template.template, "  "))
# 3. Create a structured output chain
llm = getLLM()
debug_print(f"LLM Initialized: {llm}")
structured_llm = llm.with_structured_output(Lecture)
chain = prompt_template | structured_llm

debug_print("Structured LLM Chain Created.")

def refine_lecture_content(retrieved_content: List[Dict[str, Any]], persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a refined lecture script from raw content based on a student persona.

    Args:
        retrieved_content: A list of dictionaries, each representing a piece of content (text or image).
        persona: A dictionary describing the student.

    Returns:
        A dictionary containing the generated 'lectureScript' and a list of 'Images'.
    """
    # Convert persona object to a dictionary if needed (e.g., for Pydantic models)
    if hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = dict(persona)

    # Ensure the ID is a string for JSON compatibility
    if 'id' in persona_dict:
        persona_dict['id'] = str(persona_dict['id'])

    # Invoke the chain with the necessary inputs
    result = chain.invoke({
        "persona": json.dumps(persona_dict, ensure_ascii=False),
        "retrieved_content": json.dumps(retrieved_content, ensure_ascii=False)
    })
    
    # Convert the Pydantic object to a dictionary to match the return type
    return result.model_dump()

if __name__ == '__main__':
    # This is an example of how to run the script generation service.
    # In a real application, this would be called by a higher-level service
    # that has already retrieved content and has access to the user's persona.

    # 1. Define sample retrieved content (e.g., from a vector database)
    sample_retrieved_content = [
        {
            "text": "The water cycle is the path that all water follows as it moves around Earth in different states. Liquid water is found in oceans, rivers, lakes, and even underground. Solid ice is found in glaciers, snow, and at the North and South Poles. Water vapor—a gas—is in the atmosphere.",
            "source": "https://education.nationalgeographic.org/resource/water-cycle/"
        },
        {
            "image": "https://education.nationalgeographic.org/resource/water-cycle/water-cycle.jpeg",
            "description": "A diagram illustrating the water cycle, showing evaporation, condensation, precipitation, and collection.",
            "source": "National Geographic"
        },
        {
            "text": "Key processes in the water cycle are evaporation, transpiration, condensation, precipitation, and runoff. Evaporation turns liquid water into a gas (water vapor). Transpiration is the release of water vapor from plants. Condensation turns water vapor back into liquid, forming clouds. Precipitation is water that falls from the sky, like rain or snow.",
            "source": "https://gpm.nasa.gov/education/water-cycle"
        }
    ]

    # 2. Define a sample student persona
    sample_persona = {
        "id": "student-123",
        "name": "Leo",
        "age": 9,
        "learning_style": "Visual",
        "prior_knowledge": "Knows that rain comes from clouds, but not much else about the process.",
        "interests": ["dinosaurs", "space", "drawing"]
    }

    # 3. Generate the refined lecture content
    print("Generating lecture content for the persona...")
    generated_lecture = refine_lecture_content(sample_retrieved_content, sample_persona)

    # 4. Print the results
    print("\n--- Generated Lecture Script ---")
    print(generated_lecture.get('lectureScript', 'No script generated.'))
    print("\n--- Associated Images ---")
    for img in generated_lecture.get('Images', []):
        print(f"- Image: {img.get('image')}, Description: {img.get('description')}")
