import typing

from fastapi import FastAPI

app = FastAPI(title="orpheus-service-slides")


@app.get("/")
async def root() -> typing.Any:
    return {"message": "Hello, AI world!"}
