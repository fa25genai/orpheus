# Document Intelligence Service

Processes lecture material such as slides and videos to produce a queryable knowledge pool; provides lookup functionality to core.

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Run using Docker](#run-using-docker)
- [Local Setup](#local-setup)
- [Quality Checks](#quality-checks)

## Technology Stack

### Currently Used Frameworks
- **Self-hosted models:** Gemma, LLaMA (llama3.3), Nomic (nomic-embed-text)  
- **Database:** Weaviate (combines vector and relational DB; supports `WHERE` statements and “foreign key”-like logic)  
- **Backend:** FastAPI (Python)  
- **Dependency management:** Poetry  
- **Containerization:** Docker (for containerized development with hot-reload)  
- **LLM for text extraction:** Gemma 27 B (used; Gemma 4 B & 12 B were not good)  
- **API interaction:** OpenAPI code generator (openapi-generator) 
- **Speech-to-text:** Whisper on Azure
- **PDF image extraction:** supports PNGs/JPEGs currently. (Recommendation: Add **LayoutParser** or similar to identify areas of interest (e.g., graphics) for richer PDF image extraction.)
- **Weaviate interaction:** mixture of pure HTTP requests and `weaviate-client` Python library 

### Good Experiences
- **Weaviate:** Great because it merges vector and relational DB features in one and supports flexible queries (`WHERE`, “foreign key” logic).  
- **FastAPI & Python:** FastAPI worked well; Python libraries made PDF processing easy.  
- **Poetry:** Excellent for dependency management; avoided almost all dependency conflicts across the team.  
- **Docker:** Enabled containerized development with hot-reload → much faster development workflow.  
- **Gemma 27 B:** Very good for text extraction — could handle math formulas, tables, and convert content back to LaTeX.  
- **OpenAPI code generator:** Worked well for generating client code. 

### Bad / Limitations
- **Gemma 4 B & 12 B:** Poor performance for text extraction.  
- **Whisper (Azure):** Rate-limited to 3 requests × 25 MB every 30 s → dependency on Azure; need open-source, self-hosted alternative.  
- **PDF image extraction:** Limited to PNG/JPEG; no layout-based extraction yet.  
- **Weaviate interaction:**  
  - Using raw HTTP requests for uploads sometimes unstable.  
  - Retrieval via HTTP broke — fixed by switching to `weaviate-client`.  
  - Documentation for `weaviate-client` still lacking. 

## Setup

Create a `.env` file and populate the environment variables.

```
cp .env.example .env
```

## Run using Docker

Use the following commands:

```
docker compose up --build -d
```

## Dockerized Development

`uvicorn` is actively watching for code changes, even while using Docker. This means, you can continue developing locally, and the code changes will automatically get reflected in Docker.

## Local Setup

```bash
cd document-intelligence
poetry install
```

## Quality Checks

```bash
poetry run ruff check .
poetry run mypy src
```
