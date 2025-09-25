## Orpheus Core AI Service
The Orpheus System transforms static slides into interactive lecture videos with lifelike professor avatars, combining expressive narration, visual presence, and dynamic content to create engaging, personalized learning experiences.

This service is the core backend component responsible for orchestrating the AI-driven content generation.

# Prerequisites

- Python 3.13.7
- [openapi-generator](https://formulae.brew.sh/formula/openapi-generator) 7.15.0

```bash 
cd core && poetry install
```

# Development Workflow
This project uses a schema-first approach. The single source of truth for the API's structure is the OpenAPI specification file.

1. Modifying the API
If you need to add, remove, or change an endpoint, you must edit the [answer_generation_service.yaml](../../../api/answer_generation_service.yaml) file first.

2. Generating API Code
After modifying the YAML schema, you must regenerate the server's boilerplate code. Run the following command from the `core` directory:
```bash
openapi-generator generate -i ../api/answer_generation_service.yaml -g python-fastapi -o . --package-name service_core --additional-properties=sourceFolder=src --ignore-file-override ./.openapi-generator-ignore --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false
```

3. Implementing Logic
- The generator is configured to keep your custom logic separate from the generated code.
- Generated Code (**DO NOT EDIT**): Files in `src/service_core/apis/` like `core_api.py` and `core_api_base.py` will be overwritten on each generation.

Your Logic (**EDIT HERE**): All your business logic should be implemented in the `src/service_core/impl/core_api_impl.py` file. This file is designed to be safe and will not be overwritten.

# Running the Service
1. Run the API Server

```
poetry run uvicorn src.service_core.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

## Running with Docker (**ONLY CORE SERVICE**)

To build and run the service using Docker, execute the following commands from the root of the `core` directory:

```sh
docker build -t service-core .

docker run --name core-ai -it --rm -p 8000:8000 service-core
```

This will build the image and start the service on port 8000.

## Testing with Docker (**WITH DOCINT INTG.**)
Open a terminal and run:
```sh
docker network create orpheus-network
cd document-intelligence
docker build -t docint-app .
docker run --network orpheus-network --name docint-app -p 25565:25565 docint-app
```
In another terminal, run:
```sh
cd core
docker build -t service-core .
docker run --network orpheus-network --name core-ai -p 8000:8000 service-core
```