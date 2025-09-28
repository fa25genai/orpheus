# llm.py
# Helper functions for interacting with LLMs via Bedrock Converse API.
# Author: Lukas Bäurle (st187218@stud.uni-stuttgart.de)
import json
from typing import TypeVar, Type
import boto3
from pydantic import BaseModel, ValidationError
from debug import debug_print

# --- FIX 1: Define a TypeVar for the Pydantic model ---
# This allows the function to return the *specific* subclass of BaseModel it receives.
T = TypeVar("T", bound=BaseModel)


class StandardResponse(BaseModel):
    answer: str


# --- FIX 2: Correct the function signature ---
# Use `Type[T]` to specify that ResponseModel is a *class* that inherits from BaseModel.
# The return type is `T`, meaning it returns an *instance* of that same class.
def ask_llm_with_model(prompt: str, ResponseModel: Type[T]) -> T:
    """
    Get a structured response from Bedrock Converse API using a Pydantic model for schema validation.
    Args:
        ResponseModel (Type[T]): A Pydantic model class defining the expected response structure.
        prompt (str): The prompt to send to the LLM.
    Returns:
        T: An instance of ResponseModel populated with the LLM's response.
    Raises:
        RuntimeError: If the LLM call fails or the response cannot be validated.
    """
    debug_print("Starting structured response generation...")
    debug_print(f"Got user prompt: {prompt}")
    try:
        schema_json = ResponseModel.model_json_schema()
    except AttributeError:
        raise RuntimeError(
            "Pydantic model must have model_json_schema method. Use Pydantic v2."
        )
    debug_print("Converted Pydantic model to JSON Schema successfully.")
    debug_print(f"Pydantic JSON Schema: {json.dumps(schema_json, indent=2)}")

    debug_print("Creating Bedrock Converse API client...")
    model_id = "eu.mistral.pixtral-large-2502-v1:0"
    region = "eu-central-1"
    debug_print(f"Using model: {model_id}")
    debug_print(f"Using region: {region}")
    client = boto3.client("bedrock-runtime", region_name=region)
    debug_print("Bedrock client created successfully.")
    debug_print("Preparing Converse API request...")
    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "OutputJson",
                    "description": "You must generate output matching the JSON schema. So you must use this tool.",
                    "inputSchema": {"json": schema_json},
                }
            }
        ]
    }
    debug_print(
        f"Created tool config with JSON schema: {json.dumps(tool_config, indent=2)}"
    )

    request_body = {
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "toolConfig": tool_config,
        "inferenceConfig": {},
    }
    debug_print(f"Final request body: {json.dumps(request_body, indent=2)}")

    # The while loop is for retries. Let's make it more explicit.
    max_retries = 3
    for attempt in range(max_retries):
        try:
            debug_print(
                f"Calling Bedrock Converse API (Attempt {attempt + 1}/{max_retries})..."
            )
            try:
                resp = client.converse(modelId=model_id, **request_body)
            except Exception as e:
                raise ConnectionRefusedError(
                    f"Bedrock Converse API call failed: {e}"
                ) from e

            debug_print("Received response from Bedrock Converse API.")
            debug_print(f"Full response: {json.dumps(resp, indent=2)}")

            contents = resp.get("output", {}).get("message", {}).get("content", [])
            tool_use = next((c for c in contents if "toolUse" in c), None)

            if not tool_use:
                raise RuntimeError(
                    "Model did not use the provided tool to generate JSON."
                )

            model_text = json.dumps(tool_use["toolUse"]["input"])
            debug_print(f"Extracted model text from tool use: {model_text}")

            parsed = json.loads(model_text)
            debug_print(f"Parsed model text: {json.dumps(parsed, indent=2)}")

            # Validate with Pydantic
            # --- FIX 3: Do not redefine 'validated' ---
            # Simply assign the result. `mypy` knows the type from the function signature.
            validated = ResponseModel(**parsed)
            debug_print(f"Validated: {validated.model_dump_json()}")

            # --- FIX 4: Return immediately on success ---
            # This makes the control flow clearer and guarantees the return type.
            return validated

        except (
            RuntimeError,
            ValidationError,
            json.JSONDecodeError,
            ConnectionRefusedError,
        ) as e:
            debug_print(f"Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:  # If this was the last attempt
                raise RuntimeError(
                    "LLM call failed to produce a valid response after all retries."
                ) from e

    # This line should ideally not be reachable if the loop is structured correctly
    raise RuntimeError("LLM call failed unexpectedly.")


def ask_llm(prompt: str) -> str:
    """
    Simple wrapper to get a standard text response from the LLM.
    """
    # --- FIX 5: Remove the redundant wrapper ---
    # `ask_llm_with_model` already returns a fully-formed `StandardResponse` object.
    response = ask_llm_with_model(prompt, StandardResponse)
    return response.answer


if __name__ == "__main__":
    # Example usage
    try:
        response = ask_llm("What is the capital of France?")
        print(f"LLM Response: {response}")
    except RuntimeError as e:
        print(f"Error: {e}")
