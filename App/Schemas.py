import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: Optional[str] = "buyer"  # buyer, seller, admin, superadmin

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

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["buyer", "seller", "admin", "superadmin"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    is_verified: bool
    is_locked: bool

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
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

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
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

class ResendVerificationTokenRequest(BaseModel):
    email: EmailStr

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class FieldsForAddress(BaseModel):
    full_name: str
    phone: str
    address_line_1: str
    city: str

# Backward compatibility aliases
resendingtoken = ResendVerificationTokenRequest
update_profile = UpdateProfileRequest
feilds_for_address = FieldsForAddress

class defaultaddress(BaseModel):
    default: bool

class UpdateUserByAdmin(BaseModel):
    role: Optional[str] = None
    is_verified: Optional[bool] = None
    is_locked: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["buyer", "seller", "admin", "superadmin"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v

