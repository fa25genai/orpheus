from fastapi import HTTPException, Request
from uuid import UUID, uuid4
from typing import Dict
import httpx
# Import the base class you are inheriting from
from service_core.apis.core_api_base import BaseCoreApi
# Import the generated Pydantic models
from service_core.models.prompt_request import PromptRequest
from service_core.models.prompt_response import PromptResponse
from service_core.models.data_response import DataResponse
# Import your custom service layer where the real work happens
from service_core.services import decompose_input, generate_lecture_content, fetch_mock_data, narration_generation
import asyncio
import json
from service_core.services.client_handler import process_prompt


lecture_script = """"
In this lecture, we will be covering the concept of for loops in programming.
A for loop is a control flow statement for specifying iteration, which allows code to be executed repeatedly. It is typically used to iterate over a sequence (like a list, tuple, or string) or a range of numbers. See image: For loop example, as an illustration of how this works.
Let's consider a worked example of a for loop in Python. A for loop is often used with the range() function to execute a block of code a specific number of times. For instance, the code 'for i in range(5): print("Hello!")' will run the print statement five times. In each iteration, the code inside the loop is executed. After the fifth time, the loop concludes and the program continues on to the next line."""
class CoreApiImpl(BaseCoreApi):
    """
    This is the implementation of the Core API.
    The router in core_api.py will discover this class and call its methods.
    """
    async def create_lecture_from_prompt(
        self,
        request: Request,
        prompt_request: PromptRequest,
    ) -> PromptResponse:
        """
        Accepts a user prompt and initiates a job to generate lecture content.
        """
        try:
            #decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
            #print("Decomposed Questions:", decomposed_questions)
            #print("Simulating async processing delay...")
            #await asyncio.sleep(5)
            #refined_output = generate_lecture_content.refine_lecture_content(fetch_mock_data.retrieved_content, fetch_mock_data.demo_user)
            #print(refined_output)
            #lecture_script = refined_output.get("lectureScript", "")
            #print("\n\nGenerated Lecture Script:", lecture_script)
            example_slides = fetch_mock_data.slide_bullets
            #print("\nExample Slides:", example_slides)
            voice_track = narration_generation.generate_narrations(lecture_script, example_slides, fetch_mock_data.demo_user)
            print("\voice_track:", voice_track)

            prompt_id = uuid4()

            executor = request.app.state.executor
            executor.submit(process_prompt, prompt_id, prompt_request.prompt)
        
            return PromptResponse(promptId=prompt_id)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
    