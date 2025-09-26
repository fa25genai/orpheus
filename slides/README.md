``# Orpheus **Slide Generation Service**

Slide generation and delivery service for **Orpheus**.
This directory contains the project code for the **Slide Generation Service**.
The [postprocessing](postprocessing/README.md) directory contains the project code for the **Slide Postprocessing Service**.
The [delivery](delivery/README.md) directory contains the configuration file for the **Generated Slide Service**.

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
| `SPLITTING_MODEL`             | Name of the LLM, which should be used to perform distribution of the lecture content across slides. |                                      |
| `SLIDESGEN_MODEL`             | Name of the LLM, which should be used to generate the slide content                                 |                                      |
| `POSTPROCESSING_SERVICE_HOST` | Base URL of where to reach the **Slide Postprocessing Service**                                     | `http://slides-postprocessing:30607` |
| `STATUS_SERVICE_HOST`         | Base URL of where to reach the **Generation Status Service**                                        | `http://status-service:19910`        |

Depending on the selected LLM models, the appropriate environment variables with API secrets have to be defined as well.
Please refer to the [.env.example](.env.example) file for further details.
