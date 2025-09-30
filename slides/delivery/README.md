# Orpheus **Generated Slides Service**

This component serves previously generated slidesets to use in the frontend.

The following path schemas are available:

| Schema                                                                  | Description                                           |
|-------------------------------------------------------------------------|-------------------------------------------------------|
| `${BASE_PATH}/web/{promptId}/` `${BASE_PATH}/web/{promptId}/index.html` | Access the compiled slideset for the given `promptId` |
| `${BASE_PATH}/pdf/{promptId}.pdf`                                       | Access the exported pdf for the given `promptId`      |
