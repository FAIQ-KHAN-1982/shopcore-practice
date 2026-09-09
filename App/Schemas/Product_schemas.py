import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class CategoryCreateSchema(BaseModel):
    name: str
    slug: str
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0