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

TODO - Document the frameworks currently in use

### Good/Bad Experiences

TODO - Document experiences, lessons learned, and recommendations

## Run using Docker

Use the following commands:

```
docker build -t docint-app .

docker run -p 25565:25565 -v "$(pwd)/src:/app/src" --env-file .env docint-app
```

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
