# === Stage 1: Base image with Python and Poetry ===
FROM python:3.13.7-slim AS poetry-base

ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install "poetry==$POETRY_VERSION"

# === Stage 2: Image with application code and dependencies ===
FROM poetry-base

# Install system dependencies, including Node.js, npm, and git
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    nodejs \
    npm && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get autoremove --yes && \
    apt-get clean && \
    rm -rf /tmp/* /var/tmp/*

# Install Slidev and its dependencies
RUN npm install -g @pnpm/exe playwright-chromium && \
    npx playwright install-deps && \
    git clone https://github.com/fa25genai/slidev.git /install/slidev/ && \
    cd /install/slidev && \
    pnpm install && \
    pnpm -w build && \
    ln -s /install/slidev/packages/slidev/bin/slidev.mjs /usr/local/bin/slidev

# Working directory and file copy
WORKDIR /app
COPY src src
COPY pyproject.toml README.md ./

# Add predefined sli.dev themes
ADD themes/slidev-theme-tum-0.1.0.tgz /etc/slidev/themes/theme-tum/
RUN cd /etc/slidev/themes/theme-tum/package && \
    npm install && \
    npm cache clean --force

# Install Python dependencies
RUN poetry install --only main

EXPOSE 30607

CMD ["poetry", "run", "uvicorn", "service_slides_postprocessing.main:app", "--host", "0.0.0.0", "--port", "30607"]