from fastapi import FastAPI

app = FastAPI(title="services-core")

@app.get("/")
async def root():
    return {"message": "Hello, AI world!"}
