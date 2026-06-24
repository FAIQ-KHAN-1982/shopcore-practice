
# --- IMPORTS ---
import re
import bcrypt
from datetime import datetime, timedelta
from jose import jwt

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
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    is_verified: bool

    class Config:
        from_attributes = True


# ==========================================
# 4. SECURITY UTILS (app/security/...)
# ==========================================
# -- hashing.py --
def hash_password(password: str):
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# -- tokens.py --
SECRET_KEY = "super-secret-key-change-this"
ALGORITHM = "HS256"

def create_verification_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ==========================================
# 5. BUSINESS LOGIC (app/services/auth_service.py)
# ==========================================
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, data):
    existing = get_user_by_email(db, data.email)
    if existing:
        raise ValueError("Email already exists")

    verification_token = create_verification_token(data.email)

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        verification_token=verification_token,
        token_expires_at=datetime.utcnow()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, verification_token


# ==========================================
# 6. FASTAPI APP & ROUTES (app/main.py + app/routers/auth.py)
# ==========================================
app = FastAPI()

# Create tables in the database (from main.py)
Base.metadata.create_all(bind=engine)

# Instead of using an APIRouter, we can define the route directly on `app`
# when everything is in one file.
@app.post("/auth/register", response_model=UserResponse, status_code=201, tags=["Auth"])
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    try:
        new_user, token = create_user(db, user)
        # IMPORTANT: send email here (not implemented yet)
        # send_verification_email(new_user.email, token)
        return new_user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
