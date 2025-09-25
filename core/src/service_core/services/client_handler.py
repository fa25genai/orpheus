import httpx
from service_core.services import decompose_input, fetch_mock_data, script_generation, narration_generation
from service_core.services.fetch_mock_data import create_context_mock

client = httpx.AsyncClient()

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "https://slides:30606"


async def process_prompt(prompt_id: str, prompt_request: str): # TODO: type prompt_request
    """
    Asynchronously calls the appropriate external API to get the final result.
    """
    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    subqueries = decomposed_questions.get("subqueries", [])
    print("Subqueries:", subqueries)

    retrieved_content = []

    for idx, subquery in enumerate(subqueries):
        print(f"\nProcessing subquery {idx + 1}/{len(subqueries)}: {subquery}")
        # Call Decompose Input API
        di_response = await client.get(
            f"{DI_API_URL}/v1/retrieval/abc",
            params={"courseId": "abc", "promptQuery": str(subquery)},
            timeout=300.0,
        )
        di_response.raise_for_status()
        di_data = di_response.json()
        print("Decompose Input API response:", di_data)
        
        entry = {
            "Question": subquery,
            "retrieved_content": di_data.get("content", []),
            "retrieved_images_descriptions": [img.get("description", "") for img in di_data.get("images", [])],
        }

        retrieved_content.append(entry)
    
    print("\nAll retrieved content:", retrieved_content)

    #print("Simulating async processing delay...")
    #await asyncio.sleep(5)
    refined_output = script_generation.generate_script(str(fetch_mock_data.create_demoretrieved_content()), fetch_mock_data.create_demo_user())
    #print(refined_output)
    lecture_script = refined_output.get("lectureScript", "")

    context_mock = create_context_mock(prompt_request.courseId, prompt_id, lecture_script, fetch_mock_data.create_demo_user())
    slides_response = await client.post(
            f"{SLIDES_API_URL}/v1/slides/generate",
            json=context_mock,
            timeout=300.0,
        )
    print("Slides API response:", slides_response.json())
    #print("\n\nGenerated Lecture Script:", lecture_script)
    #example_slides = fetch_mock_data.create_demo_slides()
    #print("\nExample Slides:", example_slides)
    #voice_track = narration_generation.generate_narrations(lecture_script, example_slides, fetch_mock_data.create_demo_user())
    #print("\nvoice_track:", voice_track)