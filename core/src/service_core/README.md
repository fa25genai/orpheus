Orpheus Core AI Service
The Orpheus System transforms static slides into interactive lecture videos with lifelike professor avatars, combining expressive narration, visual presence, and dynamic content to create engaging, personalized learning experiences.

This service is the core backend component responsible for orchestrating the AI-driven content generation.

Prerequisites
Before you begin, ensure you have the following software installed:

Python 3.13+

Poetry: For managing Python dependencies.

Docker: For running external services like the data store.

Homebrew (macOS): For easily installing openapi-generator.

openapi-generator: The tool used to generate API code from the schema.

# Install with Homebrew on macOS
brew install openapi-generator

Setup Instructions
Clone the repository (if you haven't already):

git clone <your-repository-url>
cd core

Install dependencies:
Use Poetry to create a virtual environment and install all required packages from the poetry.lock file.

poetry install

Development Workflow
This project uses a schema-first approach. The single source of truth for the API's structure is the OpenAPI specification file.

1. Modifying the API

If you need to add, remove, or change an endpoint, you must edit the service_core_v1.yaml file first.

2. Generating API Code

After modifying the YAML schema, you must regenerate the server's boilerplate code. Run the following command from the project root:

openapi-generator generate \
    -i service_core_v1.yaml \
    -g python-fastapi \
    -o . \
    --package-name service_core \
    --additional-properties=sourceFolder=src

-o .: Outputs to the current directory.

--package-name service_core: Sets the Python package name.

--additional-properties=sourceFolder=src: Uses the src layout.

3. Implementing Business Logic

The generator is configured to keep your custom logic separate from the generated code.

Generated Code (DO NOT EDIT): Files in src/service_core/apis/ like core_api.py and core_api_base.py will be overwritten on each generation.

Your Logic (EDIT HERE): All your business logic should be implemented in the src/service_core/impl/core_api_impl.py file. This file is designed to be safe and will not be overwritten.

Running the Service
1. Start the Datastore

The service requires a running Valkey or Redis instance. The easiest way to run this is with Docker.

# We recommend Valkey, a drop-in Redis alternative
docker run -d -p 6379:6379 --name orpheus-valkey valkey/valkey

2. Run the API Server

Use uvicorn to run the FastAPI application. The --reload flag is recommended for development as it automatically restarts the server when you save changes.

poetry run uvicorn src.service_core.main:app --reload

The server will be available at http://127.0.0.1:8000.

Testing the API
Once the server is running, you can use the interactive Swagger UI documentation to test your endpoints.

Open the Docs:
Navigate to http://localhost:8000/docs in your web browser.

Test the prompt Endpoint:

Expand the POST /core/prompt endpoint.

Click "Try it out".

Enter a prompt in the request body, e.g., { "prompt": "Explain gravity" }.

Click "Execute".

Copy the lectureId from the successful response.

Test the getSlides Endpoint:

Expand the GET /core/getSlides/{lectureId} endpoint.

Click "Try it out".

Paste the copied lectureId into the parameter field.

Click "Execute" to get the slide data.

