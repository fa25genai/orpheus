# In: my-templates/Dockerfile.mustache

# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Poetry from creating a new virtual environment inside the container
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

# Install Poetry
RUN pip install poetry

# Copy the dependency files
COPY pyproject.toml poetry.lock ./

# Install project dependencies (without dev dependencies)
# This creates a cache layer for dependencies, speeding up subsequent builds.
RUN poetry install --no-root --no-dev

# Copy the rest of the application's source code
COPY ./src ./src

# The port that the application will run on
EXPOSE 8000

# The command to run the application
# For production, we use --host 0.0.0.0 to make it accessible outside the container.
# The --reload flag should NOT be used in production.
CMD ["poetry", "run", "uvicorn", "src.service_core.main:app", "--host", "0.0.0.0"]