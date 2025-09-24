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

1. Generate them for the core
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../core/service_core_v1.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/core
    ```
2. Generate them for the avatar
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../avatar/service_video_v1.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/avatar
    ```
3. Generate them for slides
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../slides/service_slides_v1.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/slides
    ```

4. Generate them for document-intelligence
    ```bash
    pnpm exec openapi-generator-cli generate \
    -i ../document-intelligence/service_document-intelligence_v1.yaml \
    -g typescript-fetch \
    -o ./generated-api-clients/document-intelligence
    ```

### Docker setup
1. How to create the docker image
    ```bash
    docker build -t nextjs-docker .
    ```
2. How to run the docker container
    ```bash
    docker run -p 3000:3000 nextjs-docker
    ```
