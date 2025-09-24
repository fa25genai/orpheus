import httpx
from service_core.services import decompose_input, generate_lecture_content, fetch_mock_data, narration_generation

client = httpx.AsyncClient()

DI_API_URL = "https://slides:8050"
SLIDES_API_URL = "https://videos:8050"


async def process_prompt(prompt_id: str, prompt_request: str):
    """
    Asynchronously calls the appropriate external API to get the final result.
    """
    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    print("Decomposed Questions:", decomposed_questions)
    #print("Simulating async processing delay...")
    #await asyncio.sleep(5)
    refined_output = generate_lecture_content.refine_lecture_content(str(fetch_mock_data.create_demoretrieved_content()), fetch_mock_data.create_demo_user())
    #print(refined_output)
    lecture_script = refined_output.get("lectureScript", "")
    print("\n\nGenerated Lecture Script:", lecture_script)
    example_slides = fetch_mock_data.create_demo_slides()
    #print("\nExample Slides:", example_slides)
    voice_track = narration_generation.generate_narrations(lecture_script, example_slides, fetch_mock_data.create_demo_user())
    print("\nvoice_track:", voice_track)