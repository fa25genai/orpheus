# Core Service

Provides chat service and orchestrates efforts by other services


Valkey:
docker run -d -p 6379:6379 --name orpheus-valkey valkey/valkey

yaml model generation:
datamodel-codegen --input service_core_v1.yaml --output src/service_core/models/model.py --input-file-type openapi

openapi gen:
openapi-generator generate -i service_core_v1.yaml -g python-fastapi -o ./src  