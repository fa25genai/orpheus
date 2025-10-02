# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV POETRY_VERSION=2.2.1 \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (minimal, headless)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        build-essential \
        ninja-build \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

# Copy project metadata first for layering
COPY pyproject.toml ./
COPY README.md ./

# Configure Poetry to install into system site-packages
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

# Install Torch (CPU), Torchvision (CPU), then Detectron2 (build from source - main)
# Note: building detectron2 from source requires compilers (installed above).
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir torch torchvision \
 && pip install --no-cache-dir --no-build-isolation \
    "detectron2@git+https://github.com/facebookresearch/detectron2.git@main#egg=detectron2"

# Now copy source
COPY src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8156

CMD ["uvicorn", "slidefigs.service:app", "--host", "0.0.0.0", "--port", "8156"]
