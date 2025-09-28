################################################################################
#                                                                              #
#                      ####### BADEN-WÜRTTEMBERG #######                       #
#                                                                              #
#          A tribute to the land of innovation, culture, and nature.           #
#          Home of Lake Constance, Bosch, Heidelberg, and Maultaschen.         #
#                                                                              #
#                         o__      o__      o__                                #
#                        / < \_   / < \_   / < \_                              #
#                       (*)/ (*) (*)/ (*) (*)/ (*)                             #
#                                                                              #
#                  "Wir können alles. Außer Hochdeutsch."                      #
#                                                                              #
################################################################################
import json
import boto3
from pydantic import BaseModel, ValidationError
from debug import debug_print


class StandardResponse(BaseModel):
    answer: str
def ask_llm_with_model(prompt: str, ResponseModel: BaseModel) -> BaseModel:
    """
    Get a structured response from Bedrock Converse API using a Pydantic model for schema validation.
    Args:
    +
        ResponseModel (BaseModel): A Pydantic model class defining the expected response structure.
        prompt (str): The prompt to send to the LLM.
    Returns:
        An instance of ResponseModel populated with the LLM's response.
    Raises:
        RuntimeError: If the LLM call fails or the response cannot be validated.
        """
        # --- 1) Define Pydantic model and get JSON Schema ---
    debug_print("Starting structured response generation...")
    debug_print(f"Got Pydantic model: {ResponseModel.__name__}")
    debug_print(f"Got user prompt: {prompt}")
    debug_print(f"Generating structured response with model: {ResponseModel.__name__}")
    try:
        schema_json = ResponseModel.model_json_schema()
    except AttributeError:
        raise RuntimeError("Pydantic model must have model_json_schema method. Use Pydantic v2.")
    debug_print("Converted Pydantic model to JSON Schema successfully.")
    debug_print(f"Pydantic JSON Schema: {json.dumps(schema_json, indent=2)}")

    # --- 2) Call Bedrock Converse with toolConfig containing the schema ---
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
                    "inputSchema": {
                        "json": schema_json
                    }
                }
            }
        ]
    }
    debug_print(f"Created tool config with JSON schema: {json.dumps(tool_config, indent=2)}")

    request_body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            prompt
                        )
                    }
                ]
            }
        ],
        "toolConfig": tool_config,
        "inferenceConfig": {}
    }
    debug_print(f"Final request body: {json.dumps(request_body, indent=2)}")
    not_done = True
    validated = None
    while not_done:
        try:
            debug_print("Calling Bedrock Converse API...")
            try:
                resp = client.converse(modelId=model_id, **request_body)
            except Exception as e:
                raise ConnectionRefusedError("Bedrock Converse API call failed") from e
            # --- 3) Extract model text and parse/validate ---
            # Typical response path: resp['output']['message']['content'] -> list of content dicts with 'text'
            debug_print("Received response from Bedrock Converse API.")
            try:
                debug_print(f"Full response: {json.dumps(resp, indent=2)}")
                contents = resp.get("output", {}).get("message", {}).get("content", [])
                text_blocks = []
                for c in contents:
                    # each c might be {"text": "..."} or other block types depending on model
                    if "text" in c:
                        text_blocks.append(c["text"])
                model_text = "".join(text_blocks).strip()
                debug_print(f"Extracted model text: {model_text}")
            except Exception as e:
                raise RuntimeError("Could not extract text from Converse response") from e

            # Try to load JSON (models sometimes include backticks or explanation - you'll need robust extraction)
            try:
                parsed = json.loads(model_text)
                debug_print(f"Parsed model text: {json.dumps(parsed, indent=2)}")
            except json.JSONDecodeError:
                # naive heuristic: try to extract first {...} block
                import re
                m = re.search(r"(\{[\s\S]*\})", model_text)
                if m:
                    parsed = json.loads(m.group(1))
                else:
                    raise ValueError("Could not extract JSON from model text")

            # Validate with Pydantic
            try:
                validated = ResponseModel(**parsed)
                debug_print("Validated:", validated.model_dump_json())
                not_done = False

            except ValidationError as ve:
                debug_print("Validation failed:", ve)
                debug_print("Raw model output:", model_text)
                raise RuntimeError("Response validation failed") from ve
        except RuntimeError as e:
            debug_print("Error during LLM call or validation:", str(e))
            debug_print("Retrying the LLM call...")
        except RuntimeError as e:
            debug_print("Error during LLM call or validation:", str(e))
            debug_print("Retrying the LLM call...")
        except Exception as e:
            raise RuntimeError("Unexpected error during LLM call or validation") from e
    return validated

def ask_llm(prompt:str) -> str:
    '''
    Simple wrapper to get a standard text response from the LLM.
    Args:
        prompt (str): The prompt to send to the LLM.
    Returns:
        str: The LLM's text response.
    Raises:
        RuntimeError: If the LLM call fails or the response cannot be validated.
    '''
    response = ask_llm(prompt, StandardResponse)
    return response.answer