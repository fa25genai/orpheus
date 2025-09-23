# === Stage 1: Base image with Python and Poetry ===
FROM python:3.13.7-slim AS poetry-base

ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install "poetry==$POETRY_VERSION"

# === Stage 2: Image with application code and dependencies ===
FROM poetry-base

WORKDIR /app
COPY src src
COPY pyproject.toml README.md ./

RUN poetry install --only main

EXPOSE 60303

CMD ["poetry", "run", "uvicorn", "service_slides.main:app", "--host", "0.0.0.0", "--port", "60303"]
