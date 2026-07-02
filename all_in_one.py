# the origonal one 


# --- IMPORTS ---
import re
import bcrypt
from datetime import datetime, timedelta
import jwt
import smtplib
from email.message import EmailMessage

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

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

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

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

def create_access_token(email: str, expires_delta: timedelta | None = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


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
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

def send_verification_email(to_email: str, token: str):
    msg = EmailMessage()
    msg['Subject'] = "Verify your email"
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email

    verification_link = f"http://localhost:8000/auth/verify?token={token}"
    msg.set_content(f"Please verify your email by clicking on the link:\n{verification_link}\n\nIf you did not request this, please ignore this email.")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Verification email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}. Error: {e}")
        print(f"Mock Email Content -> Link: {verification_link}")

app = FastAPI()

# ──────────────────────────────────────────────────────────
# CORS — allows the HTML/JS frontend (opened in a browser
# from a different port or file://) to call this API.
# In production, replace "*" with your actual frontend URL.
# ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # allow any origin during development
    allow_credentials=True,
    allow_methods=["*"],    # allow GET, POST, PUT, DELETE …
    allow_headers=["*"],    # allow Content-Type, Authorization …
)

# Create tables in the database (from main.py)
Base.metadata.create_all(bind=engine)

@app.get("/auth/verify", tags=["Auth"])
def verify(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token structure"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    if user.is_verified:
        return {"message": "Email is already verified"}
        
    user.is_verified = True
    user.verification_token = None
    user.token_expires_at = None
    db.commit()
    db.refresh(user)
    return {"message": "Email verified successfully"}

# Instead of using an APIRouter, we can define the route directly on `app`
# when everything is in one file.
@app.post("/auth/register", response_model=UserResponse, status_code=201, tags=["Auth"])
def register(user: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        new_user, token = create_user(db, user)
        background_tasks.add_task(send_verification_email, str(new_user.email), token)
        return new_user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(str(user.email))
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )
