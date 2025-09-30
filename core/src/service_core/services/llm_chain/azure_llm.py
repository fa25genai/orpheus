import os
import instructor
from openai import AzureOpenAI
from pydantic import BaseModel, Field

class basicAnswer(BaseModel):
    answer: str = Field(..., description="The answer.")

def azure_with_structured_output(prompt: str, answer: BaseModel) -> BaseModel:
    """
    Extracts project details from a given text using Azure OpenAI.

    Args:
        system_prompt: The system prompt for the conversation.
        user_prompt: The user prompt for the conversation.
        answer: A Pydantic model defining the expected output structure.

    Returns:
        A ProjectDetails object with the extracted information.
    """
    client = AzureOpenAI(
        api_key=os.environ.get("AZURE_API_KEY", ""),
        azure_endpoint=os.environ.get("AZURE_ENDPOINT", ""),
        api_version=os.environ.get("AZURE_API_VERSION", ""),
    )

    # 3. Wenden Sie den 'instructor'-Patch an
    # Dies fügt dem Client die Funktionalität `response_model` hinzu
    patched_client = instructor.patch(client)

    # 4. Rufen Sie die API mit `response_model` auf
    try:
        projekt_info = patched_client.chat.completions.create(
            model=os.environ.get("AZURE_MODEL", "gpt-5-mini"), # Ihr Deployment-Name
            response_model=answer, # Hier übergeben Sie das Pydantic-Modell
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return projekt_info
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def azure_with_string_output(prompt: str) -> str:
    """
    Extracts project details from a given text using Azure OpenAI.

    Args:
        system_prompt: The system prompt for the conversation.
        user_prompt: The user prompt for the conversation.
    Returns:
        A string with the extracted information.
    """
    return azure_with_structured_output(prompt, basicAnswer).answer