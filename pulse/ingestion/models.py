from pydantic import BaseModel
from typing import Optional

class Review(BaseModel):
    content: str
    score: int
    thumbsUpCount: int
