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

| Environment Variable          | Description                                                                                         | Default value                        |
|-------------------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------|
| `SPLITTING_MODEL`             | Name of the LLM, which should be used to perform distribution of the lecture content across slides. |                                      |
| `SLIDESGEN_MODEL`             | Name of the LLM, which should be used to generate the slide content                                 |                                      |
| `POSTPROCESSING_SERVICE_HOST` | Base URL of where to reach the **Slide Postprocessing Service**                                     | `http://slides-postprocessing:30607` |

Depending on the selected LLM models, the appropriate environment variables with API secrets have to be defined as well.
Please refer to the [.env.example](.env.example) file for further details.
