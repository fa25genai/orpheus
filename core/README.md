# Orpheus Core AI Service
The Orpheus System transforms static slides into interactive lecture videos with lifelike professor avatars, combining expressive narration, visual presence, and dynamic content to create engaging, personalized learning experiences.

This service is the core backend component responsible for orchestrating the AI-driven content generation.

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Prerequisites](#prerequisites)
- [Development Workflow](#development-workflow)
  - [Running the Service](#running-the-service)
  - [Running with Docker](#running-with-docker-only-core-service)
  - [Tests](#tests)
  - [Quality Checks](#quality-checks)

## Technology Stack

### Currently Used Frameworks

- [Langchain](https://www.langchain.com/) (so we can exchange the models underneath) <br>
  - We are using it more like a library right now, we only use it to instantiate the connector to the LLM
- [Amazon Nova Pro](https://eu-central-1.console.aws.amazon.com/bedrock/home?region=eu-central-1#/inference-profiles/eu.amazon.nova-pro-v1:0) (Using langchain_aws, Ollama, and Gemini are also implemented → See [/helpers/shared_llm.py](./src/service_core/services/llm_chain/shared_llm.py))
- [Docker](https://www.docker.com/) for Infrastructure
- [OpenAPI](https://www.openapis.org/) specification for endpoints (and generating code from it)
  [openapi-generator](https://formulae.brew.sh/formula/openapi-generator) 7.15.0
- [Pydantic models](https://docs.pydantic.dev/latest/api/base_model/) for data validation and type safety.

#### Following technologies are already implementated but where out of scope for demo use at Ferienakademie
They are available in different branches (but where abondend through Ferienakademie):
- AWS Amazon Bedrock Structured Output through tool use: [baeurle/aws-llm-with-structured-output](https://github.com/fa25genai/orpheus/tree/baeurle/aws-llm-with-structured-output)
- Azure OpenAI with structured output through instructor (ONLY WAY TO ENSURE CORRECT ANSWER)(no parsing needed) :[baeurle/aws-llm-with-structured-output](https://github.com/fa25genai/orpheus/tree/baeurle/aws-llm-with-structured-output)

If you have questions about these implementation (and of course other core stuff), reach out to Lukas Bäurle [st187218@stud.uni-stuttgart.de](mailto://st187218@stud.uni-stuttgart.de)

### Good/Bad Experiences

- [AWS API key](https://eu-central-1.console.aws.amazon.com/bedrock/home?region=eu-central-1#/api-keys/long-term/create) expires every hour with our current hackathon licenses <br>
    - We are using AWS models because they are much faster than the Ollama instance
    - We often ran into rate limits as we shared the keys with 3-5 people who were developing and testing the software
    - We were only able to generate short-term keys and no long-term keys.
- [Ollama](https://ollama.com/) is responding with good answers but slow
- [GPT5](https://platform.openai.com/docs/guides/latest-model) gives better script and voice tracks, but it takes too much time
- follows structured output (gives formally correct structured output, so no JSON parsing that could yield mistakes is required)
- Response parsing has to be configured based on the LLM model used
- Huge docker images that take O(10 minutes) to build
- Smaller AWS model (Nova Lite and Nova Micro) is not able to find the connection between the retrieved content and the user query

## Prerequisites

``` 
cd core
poetry install
```

## Development Workflow
This project uses a schema-first approach. The single source of truth for the API's structure is the OpenAPI specification file.

1. Modifying the API
If you need to add, remove, or change an endpoint, you must edit the `service_core_v1.yaml` file first.

2. Generating API Code
After modifying the YAML schema, you must regenerate the server's boilerplate code. Run the following command from the project root:
```
openapi-generator generate -i service_core_v1.yaml -g python-fastapi -o . --package-name service_core --additional-properties=sourceFolder=src --ignore-file-override ./.openapi-generator-ignore --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false
```

3. Implementing Logic
- The generator is configured to keep your custom logic separate from the generated code.
- Generated Code (**DO NOT EDIT**): Files in `src/service_core/apis/` like `core_api.py` and `core_api_base.py` will be overwritten on each generation.

Your Logic (**EDIT HERE**): All your business logic should be implemented in the `src/service_core/impl/core_api_impl.py` file. This file is designed to be safe and will not be overwritten.

### Running the Service
1. Run the API Server

```
poetry run uvicorn service_core.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

### Running with Docker (**ONLY CORE SERVICE**)

To build and run the service using Docker, execute the following commands from the root of the `core` directory:

```sh
docker build -t service-core .

docker run --name core-ai -it --rm -p 8000:8000 service-core
```

This will build the image and start the service on port 8000.

### Tests

To run the tests:

```bash
pip3 install pytest
PYTHONPATH=src pytest tests
```

### Quality Checks

```bash
poetry run ruff check .
poetry run mypy src
```
