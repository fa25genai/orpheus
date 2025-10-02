Slides Figure Extraction Service
================================

This project exposes a FastAPI microservice that identifies figures inside slide
images (PNG or JPEG) and returns the cropped regions as base64 encoded PNGs. The
runtime leans on `layoutparser` + Detectron2 with the PubLayNet Faster R-CNN
model so the same behaviour is available locally and in Docker.

How It Works
------------

1. An uploaded slide image is loaded with Pillow and converted to an RGB NumPy
   array.
2. `LayoutParserDetector` lazily initialises the PubLayNet Detectron2 model and
   runs inference.
3. Each figure block above the confidence threshold is cropped, converted to PNG
   in-memory, and returned to the caller together with the detection score and
   bounding box.
4. The detector downloads model weights once to `WEIGHTS_DIR` (defaults to
   `/weights`) so repeated invocations reuse cached assets.

API Surface
-----------

| Method | Path       | Description                          |
| ------ | ---------- | ------------------------------------ |
| GET    | `/healthz` | Lightweight readiness probe.         |
| POST   | `/extract` | Detect figures and return PNG crops. |

### `/extract`

Multipart form-data request with a single field named `file` (PNG/JPEG). A
successful response resembles:

```json
{
  "count": 2,
  "items": [
    {
      "score": 0.97,
      "box": {"x1": 422, "y1": 185, "x2": 739, "y2": 568},
      "image": {
        "format": "png",
        "width": 317,
        "height": 383,
        "data": "iVBORw0KGgoAAAANSUhEUgAA..."
      }
    }
  ]
}
```

When no figures are detected, the service responds with `{ "count": 0, "items": [] }`.

Configuration
-------------

| Variable              | Default     | Purpose                                                                 |
| --------------------- | ----------- | ------------------------------------------------------------------------ |
| `HOST`                | `0.0.0.0`   | Bind address for the uvicorn server.                                     |
| `PORT`                | `8156`      | HTTP port exposed by the service.                                        |
| `WEIGHTS_DIR`         | `/weights`  | Directory used to cache PubLayNet weights.                               |
| `PUBLAYNET_MODEL_URL` | Dropbox URL | Override to supply an alternative model artefact location if necessary. |

Quickstart (Local)
------------------

1. Install Poetry if needed: `pip install poetry`.
2. Install dependencies: `poetry install`.
3. Launch the API: `poetry run slidefigs-api`.
4. Interact with the service at `http://127.0.0.1:8156`.

Example extraction call:

```bash
curl -X POST \
  -F "file=@example-slide.png" \
  http://127.0.0.1:8156/extract | jq
```

Docker
------

```bash
docker build -t slides-figure-service .
docker run --rm -p 8156:8156 slides-figure-service
```

The Docker image includes CPU builds of PyTorch, Torchvision, and Detectron2 so
that the PubLayNet weights can load without extra configuration.

Notes
-----

- Running outside of Docker still requires Detectron2; ensure it is available in
  your Python environment before starting the service.
- The service performs no persistent storage of extracted figures—the PNG data
  is generated on the fly per request.
