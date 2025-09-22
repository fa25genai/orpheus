import typing

from fastapi import FastAPI
from service_slides.apis.slides_api import router as SlidesApiRouter

app = FastAPI(title="orpheus-service-slides")

app.include_router(SlidesApiRouter)

@app.get("/")
async def root() -> typing.Any:
    return {"message": "Hello, AI world!"}
