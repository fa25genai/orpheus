# === Stage 1: Base image with Python and Poetry ===
FROM python:3.13.7-slim AS poetry-base

ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install "poetry==$POETRY_VERSION"

# === Stage 2: Image with application code and dependencies ===
FROM poetry-base

# Install slidev executable (requires node)
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get update ;\
    apt-get install -y npm ;\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN npm install -g @slidev/cli@52.2.4 ;\
    npm install -g @slidev/types@52.2.4 ;\
    npm install -g playwright-chromium ;\
    npx playwright install-deps ;\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* ;\
    npm cache clean --force

WORKDIR /app
COPY src src
COPY pyproject.toml README.md ./

# Add predefined sli.dev themes
ADD themes/slidev-theme-tum.tgz /etc/slidev/themes/theme-tum/
RUN cd /etc/slidev/themes/theme-tum/package ; \
    npm install ; \
    npm cache clean --force

RUN poetry install --only main

EXPOSE 30607

CMD ["poetry", "run", "uvicorn", "service_slides_postprocessing.main:app", "--host", "0.0.0.0", "--port", "30607"]
