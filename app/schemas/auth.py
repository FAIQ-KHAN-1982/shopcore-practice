from pydantic import BaseModel, EmailStr, field_validator
import re

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain 1 uppercase letter")

        if not re.search(r"[0-9]", v):
            raise ValueError("Must contain 1 number")

        if not re.search(r"[\W_]", v):
            raise ValueError("Must contain 1 special character")

        return v


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    is_verified: bool

    class Config:
        from_attributes = True