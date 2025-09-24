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

REFINE_PROMPT = textwrap.dedent("""
You are an assistant that produces a coherent answer to a question based on the provided content and student persona.

Inputs:
- A student persona (id, role, language, preferences, enrolled cources).
- A list of retrieved content (text + images) for a lecture.                               

Task:
- Combine the retrieved content into a single lecture script.
- Adapt the content difficulty and explanation based on the student's persona.
- Make the script formal.
- Reference images inline where appropriate (e.g., "see image: <description>").
- Respond in strict JSON format:

{
  "lectureScript": "...",
  "Images": [{"image": "...", "description": "..."}]
}

Do NOT produce slides or voice scripts at this stage.
""")

def refine_lecture_content(retrieved_content: List[Dict[str, Any]], persona: Dict[str, Any]) -> Dict[str, Any]:
    if hasattr(persona, 'dict'):
        persona_dict = persona.dict()
    elif hasattr(persona, 'model_dump'):
        persona_dict = persona.model_dump()
    else:
        persona_dict = persona

    persona_dict['id'] = str(persona_dict['id'])
    
    prompt = REFINE_PROMPT + "\n\n" + json.dumps({
        "persona": persona_dict,
        "retrieved_content": retrieved_content
    }, ensure_ascii=False)
    raw = getLLM().invoke(prompt)
    try:
        return json.loads(raw)
    except Exception:
        # Fallback: try extracting JSON substring
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
        raise RuntimeError("Failed to parse JSON from LLM output: " + raw)

