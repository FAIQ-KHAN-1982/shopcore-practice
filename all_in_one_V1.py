# removed the authentication for simplicity


# --- IMPORTS ---
import re
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel, EmailStr, field_validator


# ==========================================
# 1. DATABASE SETUP (app/database.py)
# ==========================================
DATABASE_URL = "postgresql://postgres:FAIQ@localhost:5432/shopcore"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 2. DATABASE MODELS (app/models/users.py)
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==========================================
# 3. PYDANTIC SCHEMAS (app/schemas/auth.py)
# ==========================================
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

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# 4. SECURITY UTILS (app/security/...)
# ==========================================
# Removed for simplicity


# ==========================================
# 5. BUSINESS LOGIC (app/services/auth_service.py)
# ==========================================
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, data):
    existing = get_user_by_email(db, data.email)
    if existing:
        raise ValueError("Email already exists")

    user = User(
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ==========================================
# 6. FASTAPI APP & ROUTES (app/main.py + app/routers/auth.py)
# ==========================================
app = FastAPI()

# Create tables in the database (from main.py)
Base.metadata.create_all(bind=engine)

# Instead of using an APIRouter, we can define the route directly on `app`
# when everything is in one file.
@app.post("/auth/register", tags=["Auth"])
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    try:
        new_user = create_user(db, user)
        return {"message": "User created successfully", "user_id": new_user.id}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/login", tags=["Auth"])
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, credentials.email)
    if not user or user.password != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return {"message": "Login successful", "user_id": user.id}

@app.get("/users", response_model=list[UserResponse], tags=["Users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_all_users(db, skip=skip, limit=limit)
