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
    -i ../avatar/service_video_v1.yaml \
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