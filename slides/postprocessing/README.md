# Orpheus **Slide Postprocessing Service**

This component takes uploaded slidesets as [sli.dev](https://sli.dev) compatible markdown, stores it and generates a static HTML page from it.
It also provides endpoints to access the previously uploaded slidesets.

The produced artifacts are stored in a directory.
The intended usage is to mount this directory to the [Generated Slides Service](../delivery/README.md)

---

## Overview

The **Slide Postprocessing Service** provides blocking slide postprocessing.
A client can:

1. Upload a new slideset to be postprocessed and stored on the slide delivery.
2. Get the details of a previously uploaded slideset.
3. List all previously uploaded slidesets by `promptId`.

---

## Configuration

The following configuration options are available (using environment variables)

| Environment Variable       | Description                                                                                                         | Default value                  |
|----------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------|
| `SLIDES_DELIVERY_BASE_URL` | Base URL of the shared directory on the **Generated Slides Service**                                                | `http://slides-delivery:30608` |
| `SLIDE_STORAGE_BASE_PATH`  | Local file path where the files are stored. This is the path that has to be mounted to **Generated Slides Service** | `/etc/orpheus/slides/storage`  |
