from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    page: int = Field(..., example=1, description="The current page number")
    page_size: int = Field(..., example=100, description="The number of items per page")
    total_items: int = Field(..., example=500, description="The total number of items")
    total_pages: int = Field(..., example=5, description="The total number of pages")
    data: List[T]

    class Config:
        arbitrary_types_allowed = True
