# Core Service

Provides chat service and orchestrates efforts by other services

## Getting Started
### Initial Setup
1. Install the dependencies
    ```bash
    poetry install
    ```
2. Start the application
    ```bash
    poetry run uvicorn src.service_core.main:app --reload
    ```

## Update generated files
yaml model generation:
### yml model
```bash
datamodel-codegen --input service_core_v1.yaml --output src/service_core/models/model.py --input-file-type openapi
```

### OpenAPI
```bash
openapi-generator generate -i service_core_v1.yaml -g python-fastapi -o ./src  
```