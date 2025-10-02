# Orpheus **Status Service**

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Overview](#overview)
- [API-Usage](#api-usage)
- [Configuration](#configuration)

## Technology Stack

### Currently Used Frameworks

TODO - Document the frameworks currently in use

### Good/Bad Experiences

TODO - Document experiences, lessons learned, and recommendations

---

## Overview

tbd

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
