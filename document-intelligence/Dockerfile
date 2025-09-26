# Simple single-stage Dockerfile for Document Intelligence API
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set Poetry configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1

# Set working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (production only)
RUN poetry install --only=main

# Copy source code
COPY src/ ./src/

# Set working directory to src
WORKDIR /app/src

# Expose port 25565
EXPOSE 25565

# Run the application
CMD ["poetry", "run", "uvicorn", "docint_app.main:app", "--host", "0.0.0.0", "--port", "25565", "--reload"]