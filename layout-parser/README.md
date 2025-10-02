Slides Figure Extraction Service

This project provides a FastAPI microservice that accepts a slide image (PNG/JPEG) and returns all detected figures as individual images via an HTTP API.

In Docker, the service always uses LayoutParser + Detectron2 with the PubLayNet model (Figure class) for high-quality detection.

Quickstart (local)

- Install dependencies with Poetry:
  - Install Poetry if needed: pip install poetry
  - poetry install
  - Run the API: poetry run slidefigs-api
  - The service listens on http://127.0.0.1:8156

Usage

- Extract figures as JSON with base64 PNG data:
  curl -X POST \
    -F "file=@example-slide.png" \
    http://127.0.0.1:8156/extract | jq

Docker

- Build the image:
  docker build -t slides-figure-service .

- Run the container:
  docker run --rm -p 8156:8156 slides-figure-service

LayoutParser in Docker

The Docker image installs Torch (CPU), Torchvision (CPU), and Detectron2 CPU wheels, and uses the PubLayNet model via LayoutParser’s Detectron2 integration.

Notes

- The /extract endpoint returns `{ "count": 0, "items": [] }` when no figures are found.
- Running locally without Docker requires installing Detectron2 in your environment; the API expects it to be available.
