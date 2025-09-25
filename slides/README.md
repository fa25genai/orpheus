# Slides Service

Creates visual slides to support the generated lecture.

- [ ] Initial slides template  
- [x] Splitting functionality  
- [ ] Slide content generation 
- [ ] UI (prototype)           @Timo

## Development docs

Regenerate postprocessing client:

```shell
npx @openapitools/openapi-generator-cli generate -i service_slide_postprocessing_v1.yaml -g python \
 -o src \
 --global-property models,apis,modelTests=false,apiTests=false,modelDocs=false,apiDocs=false\
 --package-name service_slides.clients.postprocessing\
 --library asyncio\
 --additional-properties=hideGenerationTimestamp=true
```