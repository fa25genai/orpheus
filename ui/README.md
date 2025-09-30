## Getting Started

### Install dependencies

1. Install pnpm (on macOS with Homebrew):
    ```bash
    brew install pnpm
    ```
2. Install the dependencies:
    ```bash
    pnpm install
    ```

### Run the app

1. Start the development server:
    ```bash
    pnpm dev
    ```
2. Open the app in your browser: [http://localhost:3000](http://localhost:3000)


### Generate the api clients with the openapi yaml specifications

Run the following command from the `ui` directory:

1. Setup the openapi-generator-cli
    ```bash
    pnpm add -D @openapitools/openapi-generator-cli -g
    openapi-generator-cli version #to check your version
    ```

2. Generate them for the core
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../api/answer_generation_service.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/core
    ```
3. Generate them for the avatar
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../api/avatar_generation_service.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/avatar
    ```
4. Generate them for slides
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../api/slide_generation_service.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/slides
    ```

5. Generate them for document-intelligence
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../api/lecture_ingestion_service.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/document-intelligence
    ```

    6. Generate them for status service
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../api/generation_status_service.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/status
    ```

### Docker setup
1. How to create the docker image
    ```bash
    docker build -t nextjs-docker .
    ```
2. How to run the docker container alternatively you can use the `docker-compose.yaml`
    ```bash
    # either 
    docker run -p 3000:3000 nextjs-docker

    # or
    docker compose up
    ```

The following configuration options are available (using environment variables)

| Environment Variable          | Description                                                                                         | Default value                        |
|-------------------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------|
| `NEXT_PUBLIC_ORPHEUS_DEBUG`               | Displays additional infos in the UI for debugging                |                                      |
| `NEXT_PUBLIC_MOCK_MODE`        | Enable mock mode to use static URLs and avoid all backend requests ("true"/"1" to enable) |                                      |
| `NEXT_PUBLIC_MOCK_VIDEOS_BASE_URL` | Base URL for mock videos; each video is fetched as `${BASE_URL}{index}.mp4` (e.g., 0.mp4, 1.mp4) |                                      |
| `NEXT_PUBLIC_MOCK_SLIDES_URL`  | Full base URL for the slides embed (the URL you would normally pass as Slidev baseUrl)     |                                      |

