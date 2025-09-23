from fastapi import FastAPI

app = FastAPI(title="your-project")

@app.get("/")
async def root():
    return {"message": "Hello, AI world!"}
