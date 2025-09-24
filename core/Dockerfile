FROM python:3.13-slim


WORKDIR /app

ENV PYTHONPATH=/app/src

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
COPY README.md ./
COPY ./src ./src

RUN poetry install


EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "src.service_core.main:app", "--host", "0.0.0.0"]