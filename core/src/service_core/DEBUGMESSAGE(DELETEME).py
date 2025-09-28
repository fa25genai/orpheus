[DEBUG 2025-09-28T16:51:57.825901]: Starting structured response generation...
core                     | [DEBUG 2025-09-28T16:51:57.825943]: Got user prompt: 
core                     | You are an assistant that decomposes a student's question into concise,
core                     | retrieval-friendly sub-queries and a final answer plan.
core                     | Respond in strict JSON with keys: original_question, subqueries, answer_plan.
core                     | 
core                     | Rules:
core                     | - Keep subqueries short and focused.
core                     | - Do not add explanations outside JSON.
core                     | 
core                     | 
core                     | Question to analyze: "Explain while loops"
core                     | [DEBUG 2025-09-28T16:51:57.829830]: Converted Pydantic model to JSON Schema successfully.
core                     | [DEBUG 2025-09-28T16:51:57.829890]: Pydantic JSON Schema: {
core                     |   "properties": {
core                     |     "original_question": {
core                     |       "title": "Original Question",
core                     |       "type": "string"
core                     |     },
core                     |     "subqueries": {
core                     |       "items": {
core                     |         "type": "string"
core                     |       },
core                     |       "title": "Subqueries",
core                     |       "type": "array"
core                     |     },
core                     |     "answer_plan": {
core                     |       "anyOf": [
core                     |         {
core                     |           "type": "string"
core                     |         },
core                     |         {
core                     |           "type": "null"
core                     |         }
core                     |       ],
core                     |       "default": null,
core                     |       "title": "Answer Plan"
core                     |     }
core                     |   },
core                     |   "required": [
core                     |     "original_question",
core                     |     "subqueries"
core                     |   ],
core                     |   "title": "QueryModel",
core                     |   "type": "object"
core                     | }
core                     | [DEBUG 2025-09-28T16:51:57.829898]: Creating Bedrock Converse API client...
core                     | [DEBUG 2025-09-28T16:51:57.829902]: Using model: eu.mistral.pixtral-large-2502-v1:0
core                     | [DEBUG 2025-09-28T16:51:57.829904]: Using region: eu-central-1
core                     | 09/28/2025 04:51:57 PM INFO botocore.credentials: Found credentials in environment variables.
core                     | [DEBUG 2025-09-28T16:51:57.942936]: Bedrock client created successfully.
core                     | [DEBUG 2025-09-28T16:51:57.942979]: Preparing Converse API request...
core                     | [DEBUG 2025-09-28T16:51:57.943032]: Created tool config with JSON schema: {
core                     |   "tools": [
core                     |     {
core                     |       "toolSpec": {
core                     |         "name": "OutputJson",
core                     |         "description": "You must generate output matching the JSON schema. So you must use this tool.",
core                     |         "inputSchema": {
core                     |           "json": {
core                     |             "properties": {
core                     |               "original_question": {
core                     |                 "title": "Original Question",
core                     |                 "type": "string"
core                     |               },
core                     |               "subqueries": {
core                     |                 "items": {
core                     |                   "type": "string"
core                     |                 },
core                     |                 "title": "Subqueries",
core                     |                 "type": "array"
core                     |               },
core                     |               "answer_plan": {
core                     |                 "anyOf": [
core                     |                   {
core                     |                     "type": "string"
core                     |                   },
core                     |                   {
core                     |                     "type": "null"
core                     |                   }
core                     |                 ],
core                     |                 "default": null,
core                     |                 "title": "Answer Plan"
core                     |               }
core                     |             },
core                     |             "required": [
core                     |               "original_question",
core                     |               "subqueries"
core                     |             ],
core                     |             "title": "QueryModel",
core                     |             "type": "object"
core                     |           }
core                     |         }
core                     |       }
core                     |     }
core                     |   ]
core                     | }
core                     | [DEBUG 2025-09-28T16:51:57.943066]: Final request body: {
core                     |   "messages": [
core                     |     {
core                     |       "role": "user",
core                     |       "content": [
core                     |         {
core                     |           "text": "\nYou are an assistant that decomposes a student's question into concise,\nretrieval-friendly sub-queries and a final answer plan.\nRespond in strict JSON with keys: original_question, subqueries, answer_plan.\n\nRules:\n- Keep subqueries short and focused.\n- Do not add explanations outside JSON.\n\n\nQuestion to analyze: \"Explain while loops\""
core                     |         }
core                     |       ]
core                     |     }
core                     |   ],
core                     |   "toolConfig": {
core                     |     "tools": [
core                     |       {
core                     |         "toolSpec": {
core                     |           "name": "OutputJson",
core                     |           "description": "You must generate output matching the JSON schema. So you must use this tool.",
core                     |           "inputSchema": {
core                     |             "json": {
core                     |               "properties": {
core                     |                 "original_question": {
core                     |                   "title": "Original Question",
core                     |                   "type": "string"
core                     |                 },
core                     |                 "subqueries": {
core                     |                   "items": {
core                     |                     "type": "string"
core                     |                   },
core                     |                   "title": "Subqueries",
core                     |                   "type": "array"
core                     |                 },
core                     |                 "answer_plan": {
core                     |                   "anyOf": [
core                     |                     {
core                     |                       "type": "string"
core                     |                     },
core                     |                     {
core                     |                       "type": "null"
core                     |                     }
core                     |                   ],
core                     |                   "default": null,
core                     |                   "title": "Answer Plan"
core                     |                 }
core                     |               },
core                     |               "required": [
core                     |                 "original_question",
core                     |                 "subqueries"
core                     |               ],
core                     |               "title": "QueryModel",
core                     |               "type": "object"
core                     |             }
core                     |           }
core                     |         }
core                     |       }
core                     |     ]
core                     |   },
core                     |   "inferenceConfig": {}
core                     | }
core                     | [DEBUG 2025-09-28T16:51:57.943085]: Calling Bedrock Converse API (Attempt 1/3)...
core                     | [DEBUG 2025-09-28T16:51:59.943899]: Received response from Bedrock Converse API.
core                     | [DEBUG 2025-09-28T16:51:59.944014]: Full response: {
core                     |   "ResponseMetadata": {
core                     |     "RequestId": "8648e2c9-256b-49e7-8970-25bb5d3bf659",
core                     |     "HTTPStatusCode": 200,
core                     |     "HTTPHeaders": {
core                     |       "date": "Sun, 28 Sep 2025 16:52:00 GMT",
core                     |       "content-type": "application/json",
core                     |       "content-length": "682",
core                     |       "connection": "keep-alive",
core                     |       "x-amzn-requestid": "8648e2c9-256b-49e7-8970-25bb5d3bf659"
core                     |     },
core                     |     "RetryAttempts": 0
core                     |   },
core                     |   "output": {
core                     |     "message": {
core                     |       "role": "assistant",
core                     |       "content": [
core                     |         {
core                     |           "text": "```json\n{\n  \"original_question\": \"Explain while loops\",\n  \"subqueries\": [\n    \"What is a while loop in programming?\",\n    \"How does a while loop work?\",\n    \"What is the syntax of a while loop?\",\n    \"When should while loops be used?\",\n    \"What are common use cases for while loops?\"\n  ],\n  \"answer_plan\": \"Combine the definition, syntax, working mechanism, use cases, and examples of while loops to provide a comprehensive explanation.\"\n}\n```"
core                     |         }
core                     |       ]
core                     |     }
core                     |   },
core                     |   "stopReason": "end_turn",
core                     |   "usage": {
core                     |     "inputTokens": 251,
core                     |     "outputTokens": 125,
core                     |     "totalTokens": 376
core                     |   },
core                     |   "metrics": {
core                     |     "latencyMs": 1759
core                     |   }
core                     | }
core                     | [DEBUG 2025-09-28T16:51:59.944052]: Error on attempt 1: Model did not use the provided tool to generate JSON.
core                     | [DEBUG 2025-09-28T16:51:59.944068]: Calling Bedrock Converse API (Attempt 2/3)...
core                     | [DEBUG 2025-09-28T16:52:01.741599]: Received response from Bedrock Converse API.
core                     | [DEBUG 2025-09-28T16:52:01.741783]: Full response: {
core                     |   "ResponseMetadata": {
core                     |     "RequestId": "ebb3d689-da67-4452-9c3b-f4e59e7fe47a",
core                     |     "HTTPStatusCode": 200,
core                     |     "HTTPHeaders": {
core                     |       "date": "Sun, 28 Sep 2025 16:52:01 GMT",
core                     |       "content-type": "application/json",
core                     |       "content-length": "657",
core                     |       "connection": "keep-alive",
core                     |       "x-amzn-requestid": "ebb3d689-da67-4452-9c3b-f4e59e7fe47a"
core                     |     },
core                     |     "RetryAttempts": 0
core                     |   },
core                     |   "output": {
core                     |     "message": {
core                     |       "role": "assistant",
core                     |       "content": [
core                     |         {
core                     |           "text": "```json\n{\n  \"original_question\": \"Explain while loops\",\n  \"subqueries\": [\n    \"What is a while loop?\",\n    \"What is the syntax of a while loop?\",\n    \"How does a while loop work?\",\n    \"What are common use cases for while loops?\",\n    \"What are examples of while loops in programming?\"\n  ],\n  \"answer_plan\": \"Define a while loop, explain its syntax and functionality, provide common use cases, and give examples.\"\n}\n```"
core                     |         }
core                     |       ]
core                     |     }
core                     |   },
core                     |   "stopReason": "end_turn",
core                     |   "usage": {
core                     |     "inputTokens": 251,
core                     |     "outputTokens": 122,
core                     |     "totalTokens": 373
core                     |   },
core                     |   "metrics": {
core                     |     "latencyMs": 1678
core                     |   }
core                     | }
core                     | [DEBUG 2025-09-28T16:52:01.741861]: Error on attempt 2: Model did not use the provided tool to generate JSON.
core                     | [DEBUG 2025-09-28T16:52:01.741883]: Calling Bedrock Converse API (Attempt 3/3)...
docint-weaviate-1        | {"build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","level":"info","msg":"Metadata FSM reported caught up, starting replication engine","time":"2025-09-28T16:52:04Z"}
docint-weaviate-1        | {"action":"replication_engine","build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","engine":{},"level":"info","msg":"starting replication engine","node":"node1","time":"2025-09-28T16:52:04Z"}
docint-weaviate-1        | {"action":"replication_engine","build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","consumer":{},"level":"info","msg":"starting replication engine consumer","node":"node1","time":"2025-09-28T16:52:04Z"}
docint-weaviate-1        | {"action":"replication_engine","build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","component":"replication_consumer","level":"info","max_workers":10,"msg":"starting replication operation consumer","node":"node1","op_timeout":86400000000000,"time":"2025-09-28T16:52:04Z"}
docint-weaviate-1        | {"action":"replication_engine","build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","level":"info","msg":"starting replication engine producer","node":"node1","producer":{},"time":"2025-09-28T16:52:04Z"}
docint-weaviate-1        | {"action":"replication_engine","build_git_commit":"2991ce6","build_go_version":"go1.24.7","build_image_tag":"v1.32.9","build_wv_version":"1.32.9","component":"replication_producer","level":"info","msg":"starting replication engine FSM producer","node":"node1","polling_interval":5000000000,"time":"2025-09-28T16:52:04Z"}
core                     | [DEBUG 2025-09-28T16:52:12.399228]: Error on attempt 3: Bedrock Converse API call failed: An error occurred (ThrottlingException) when calling the Converse operation (reached max retries: 4): Too many requests, please wait before trying again.
core                     | 09/28/2025 04:52:12 PM ERROR Client Handler: Failed processing for 1d3af0a5-0a58-4f72-8a90-e494ed2b3bcd: LLM call failed to produce a valid response after all retries.
core                     | Traceback (most recent call last):
core                     |   File "/app/src/service_core/services/helpers/llm.py", line 82, in ask_llm_with_model
core                     |     resp = client.converse(modelId=model_id, **request_body)
core                     |   File "/usr/local/lib/python3.13/site-packages/botocore/client.py", line 602, in _api_call
core                     |     return self._make_api_call(operation_name, kwargs)
core                     |            ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
core                     |   File "/usr/local/lib/python3.13/site-packages/botocore/context.py", line 123, in wrapper
core                     |     return func(*args, **kwargs)
core                     |   File "/usr/local/lib/python3.13/site-packages/botocore/client.py", line 1078, in _make_api_call
core                     |     raise error_class(parsed_response, operation_name)
core                     | botocore.errorfactory.ThrottlingException: An error occurred (ThrottlingException) when calling the Converse operation (reached max retries: 4): Too many requests, please wait before trying again.
core                     | 
core                     | The above exception was the direct cause of the following exception:
core                     | 
core                     | Traceback (most recent call last):
core                     |   File "/app/src/service_core/services/helpers/llm.py", line 84, in ask_llm_with_model
core                     |     raise ConnectionRefusedError(
core                     |         f"Bedrock Converse API call failed: {e}"
core                     |     ) from e
core                     | ConnectionRefusedError: Bedrock Converse API call failed: An error occurred (ThrottlingException) when calling the Converse operation (reached max retries: 4): Too many requests, please wait before trying again.
core                     | 
core                     | The above exception was the direct cause of the following exception:
core                     | 
core                     | Traceback (most recent call last):
core                     |   File "/app/src/service_core/services/client_handler.py", line 279, in process_prompt
core                     |     subqueries = await decompose_inputs(prompt_request, prompt_id, client)
core                     |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
core                     |   File "/app/src/service_core/services/client_handler.py", line 71, in decompose_inputs
core                     |     decomposed_questions = decompose_input.decompose_question(
core                     |                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
core                     |         prompt_request.prompt
core                     |         ^^^^^^^^^^^^^^^^^^^^^
core                     |     ).get("subqueries", [])
core                     |     ^
core                     |   File "/app/src/service_core/services/decompose_input.py", line 33, in decompose_question
core                     |     output = ask_llm_with_model(prompt, QueryModel).model_dump_json()
core                     |              ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
core                     |   File "/app/src/service_core/services/helpers/llm.py", line 123, in ask_llm_with_model
core                     |     raise RuntimeError(
core                     |         "LLM call failed to produce a valid response after all retries."
core                     |     ) from e
core                     | RuntimeError: LLM call failed to produce a valid response after all retries.
core                     | (3/8): SUCCESS: Closing CoreThreadPoolExecutor for 1d3af0a5-0a58-4f72-8a90-e494ed2b3bcd