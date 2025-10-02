# Orpheus **Slide Generation Service**

Slide generation and delivery service for **Orpheus**.
This directory contains the project code for the **Slide Generation Service**.
The [postprocessing](postprocessing/README.md) directory contains the project code for the **Slide Postprocessing Service**.
The [delivery](delivery/README.md) directory contains the configuration file for the **Generated Slide Service**.

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Overview](#overview)
- [API-Usage](#api-usage)
- [Local Setup](#local-setup)
- [Quality Checks](#quality-checks)
- [Configuration](#configuration)

## Technology Stack

### Currently Used Frameworks

For slide generation/display: [Slidev](https://sli.dev).
For Webservice serving: [Fastapi](https://fastapi.tiangolo.com/)
OpenAPI Generator
For LLM integration: [Langchain](python.langchain.com) (AWS Bedrock, Google GenAI, Ollama, OpenAI, Azure OpenAI)
For Deployment: [Docker](https://docker.com)
For Content Delivery: [nginx](https://nginx.org)
Python + Poetry as build system

### Good/Bad Experiences

**Good**:
 - Slidev being Open-Source allowed for creating a fork to alleviate the pains of embedding it into an `iframe`
 - Slidev theme creation being easy and powerful
 - Configuration via environment variables in Docker working great
 - Typed development in python allowing a better development experience
 - OpenAPI as format for communication and as basis for code generation
 - `reveal.js` would have been easier to integrate with `Next.js`, but theming was more difficult

**Bad**:
 - Integration of Slidev into Web-Frameworks (tested with Next.js, Microfrontend and Astro.js) being impossible &Rarr; Use of `iframe` necessary
 - Python `asyncio.Lock` not being threadsafe &Rarr; Use `threading.Lock` instead
 - OpenAPI Generator for fastapi not providing access to the `fastapi.Request` object (necessary to get app state) &Rarr; Manual edits in generated files necessary
 - For Postprocessing `poetry` and `npm` are necessary in the same container &Rarr; Huge image, long build times and complex recipe
 - Frequent LLM changes so no satisfying result was achieved

---

## Overview

The **Slide Generation Service** provides asynchronous slide generation for lecture content.
A client can:

1. Submit a request with a lecture script and supporting assets.
2. Poll for the status of the generation job.
3. Retrieve URLs for accessing the generated slide deck once ready.

---

## API-Usage

The intended API-Usage is to call the `/v1/slides/generate` endpoint. This will start the slide generation.
After the operation returns, the `/v1/slides/{promptId}/status` endpoint may be used to poll the generation status.
Upon completion, it will also provide the URL to access the content.
``

## Local Setup

```bash
cd slides
poetry install
```

## Quality Checks

```bash
poetry run ruff check .
poetry run mypy src
```

## Configuration

The following configuration options are available (using environment variables)

| Environment Variable          | Description                                                                                         | Default value                        |
|-------------------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------|
| `ORPHEUS_VERBOSE`             | Enable verbose logging.                                                                             |                                      |
| `ORPHEUS_DEBUG`               | Replaces all LLM interactions with predefined stand-in data (independent of inputs).                |                                      |
| `SPLITTING_MODEL`             | Name of the LLM, which should be used to perform distribution of the lecture content across slides. |                                      |
| `SLIDESGEN_MODEL`             | Name of the LLM, which should be used to generate the slide content                                 |                                      |
| `POSTPROCESSING_SERVICE_HOST` | Base URL of where to reach the **Slide Postprocessing Service**                                     | `http://slides-postprocessing:30607` |
| `STATUS_SERVICE_HOST`         | Base URL of where to reach the **Generation Status Service**                                        | `http://status-service:19910`        |

Depending on the selected LLM models, the appropriate environment variables with API secrets have to be defined as well.
Please refer to the [.env.example](exampleEnv) file for further details.
