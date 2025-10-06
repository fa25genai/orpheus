# Orpheus **UI Service**
tbd

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#goodbad-experiences)
- [Getting Started](#getting-started)
  - [Install dependencies](#install-dependencies)
  - [Run the app](#run-the-app)
  - [Generate the api clients with the openapi yaml specifications](#generate-the-api-clients-with-the-openapi-yaml-specifications)
  - [Docker setup](#docker-setup)

## Technology Stack

### Currently Used Frameworks

- [NextJS](https://nextjs.org/) 
    - Used as Metaframework to wrap React
    - Provides server-side rendering, static site generation, and routing
    - Makes the app faster and easier to scale

- [React](https://react.dev/)
    - Core reactive javascript framework
    - Enables a modular, component-based structure for reusability and maintainability

- [shadcn ui](https://ui.shadcn.com/) 
    - Prebuilt, customizable UI components built with Radix and Tailwind
    - Helps speed up development with accessible and styled components 

- [Tailwindcss](https://tailwindcss.com/) 
    - Utility-first CSS framework
    - Makes styling components faster with inline class-based styling
    - Keeps the codebase clean by avoiding large CSS files and promoting a composable design approach.

- [OpenAPI Generator](https://openapi-generator.tech/)
    - Used to generate API clients automatically from OpenAPI specifications.  
    - Reduces boilerplate when integrating with APIs
    - Ensures consistency and type safety across API calls

- [Typescript](https://www.typescriptlang.org/)
    - Enables typing to JavaScript
    - Helps catch errors at compile time instead of runtime
    - Improves code readability and maintainability



### Good/Bad Experiences

#### Good
- **TypeScript & OpenAPI Generator**  
  - Provided a strongly typed environment across the project
  - Enabled rapid updates whenever the APIs changed
  - Automatically generated clients ensured reliable API calls, preventing issues like unprocessable entities or incorrect endpoints 

- **Next.js & React**  
  - Mature and widely adopted technologies with extensive documentation  
  - Strong community support and abundant resources online
  - Well-covered by Generative AI tools, making problem-solving faster

- **shadcn/ui & Tailwind CSS**  
  - Offered a great balance between flexibility and speed of development 
  - Delivered solid starting points for UI components while still allowing custom design
  - Helped maintain a consistent and polished interface

- **Docker Integration**  
  - Easy to set up and integrate with Next.js.  
  - Simplified deployment and ensured consistent environments
  - Supported by clear and well-structured Next.js documentation


#### Bad
- **CORS & Proxy Setup**  
  - A proxy in Next.js was required to work around CORS restrictions with the Avatar Video Producer and Avatar Delivery
  - Proxies only worked reliably inside the Docker environment 

- **Development Limitations**  
  - Running the frontend in local development with `pnpm dev` and connecting to the proxied endpoints (Avatar Video Producer and Avatar Delivery) running in Docker was not possible

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

