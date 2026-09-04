import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    parent_id: int | None = None
    is_active: bool = True
    sort_order: int = 0