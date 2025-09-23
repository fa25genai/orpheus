from fastapi import APIRouter
from typing import Union

router = APIRouter()

@router.get("/")
def read_root():
    return {"Hello": "World"}

@router.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@router.get("/gettext/{course_id}")
def get_text(course_id: int, query: Union[str, None] = None):
    return {"text": f"This is a sample text for course {course_id}.", "query": query}
