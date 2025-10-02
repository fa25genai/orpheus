# Orpheus **Status Service**

Generation Status management service for **Orpheus**.
This directory contains the project code for the **Generation Status Service**.

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Overview](#overview)
- [API-Usage](#api-usage)
- [Configuration](#configuration)

## Technology Stack

### Currently Used Frameworks

For Webservice serving: [Fastapi](https://fastapi.tiangolo.com/)
OpenAPI Generator
For Deployment: [Docker](https://docker.com)
Python + Poetry as build system

### Good/Bad Experiences

**Good**:
 - Configuration via environment variables in Docker working great
 - Typed development in python allowing a better development experience
 - OpenAPI as format for communication and as basis for code generation

**Bad**:
 - Python `asyncio.Lock` not being threadsafe &rArr; Use `threading.Lock` instead

---

## Overview

The **Generation Status Service** provides endpoints for the following operations:
  - Updating a status for the lecture generated for a specific prompt
  - Querying the current status of a generation process

---

## API-Usage

The intended API-Usage is to call the `/v1/status/{promptId}/update` endpoint to apply a status patch.
To retrieve the current status either call the `/v1/status/{promptId}` endpoint to get the current status **or** open a websocket connection to `/v1/status/{promptId}/live` to receive continuous updates.

## Configuration

There are no supported configurations besides the global **`ORPHEUS_VERBOSE`**.
