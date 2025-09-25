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

## Configuration

The following configuration options are available (using environment variables)

| Environment Variable       | Description                                                                                                         | Default value                  |
|----------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------|
| `SLIDES_DELIVERY_BASE_URL` | Base URL of the shared directory on the **Generated Slides Service**                                                | `http://slides-delivery:30608` |
| `SLIDE_STORAGE_BASE_PATH`  | Local file path where the files are stored. This is the path that has to be mounted to **Generated Slides Service** | `/etc/orpheus/slides/storage`  |
