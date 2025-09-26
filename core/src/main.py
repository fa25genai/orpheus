from fastapi import FastAPI

app = FastAPI(title="services-core")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello, AI world!"}


def run() -> None:
    """Entrypoint placeholder to satisfy type checkers when executed as a script."""
    return None
