# Document Intelligence Service

Processes lecture material such as slides and videos to produce a queryable knowledge pool; provides lookup functionality to core.

# Run using Docker

Use the following commands:

```
docker build -t docint-app .

docker run -p 25565:25565 -v "$(pwd)/src:/app/src" docint-app
```