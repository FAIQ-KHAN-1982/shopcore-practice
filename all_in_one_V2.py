# the origonal one 


# --- IMPORTS ---
import re
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
import smtplib
from email.message import EmailMessage
import secrets
import hashlib

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


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
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(String, default="buyer", nullable=False)  # "buyer", "seller", "admin", "superadmin"
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Login security fields
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    # Password reset fields
    reset_token_hash = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String, nullable=True)


# ==========================================
# 3. PYDANTIC SCHEMAS (app/schemas/auth.py)
# ==========================================
# 3. PYDANTIC SCHEMAS (app/schemas/auth.py)
# ==========================================
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


# ==========================================
# 4. SECURITY UTILS (app/security/...)
# ==========================================
# -- Configurable Security Constants --
BCRYPT_ROUNDS = 12
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
MAX_LOGIN_ATTEMPTS = 5
REQUIRE_EMAIL_VERIFICATION = True

SECRET_KEY = "super-secret-key-change-this"
ALGORITHM = "HS256"

# -- hashing.py --
def hash_password(password: str):
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain, hashed):
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# -- tokens.py --
def create_verification_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(email: str, expires_delta: Optional[timedelta] = None):
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(db: Session, user_id: int, ip_address: Optional[str] = None) -> str:
    token_str = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expires_naive = expires_at.replace(tzinfo=None)
    
    refresh_token = RefreshToken(
        token=token_str,
        user_id=user_id,
        expires_at=expires_naive,
        ip_address=ip_address,
        revoked=False
    )
    db.add(refresh_token)
    db.commit()
    return token_str

def rotate_refresh_token(db: Session, token_str: str, ip_address: Optional[str] = None) -> tuple[str, str]:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token_str).first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_token_expires = db_token.expires_at.replace(tzinfo=None) if db_token.expires_at.tzinfo else db_token.expires_at
    
    if db_token.revoked or db_token_expires < now:
        # Replay attack prevention: revoke all user sessions
        revoke_all_user_tokens(db, db_token.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired or revoked. All active sessions have been invalidated."
        )
    
    # Mark old token as rotated/revoked
    db_token.revoked = True
    db.commit()
    
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    # Generate new pair
    new_access = create_access_token(user.email)
    new_refresh = create_refresh_token(db, user.id, ip_address)
    
    return new_access, new_refresh

def revoke_refresh_token(db: Session, token_str: str):
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token_str).first()
    if db_token:
        db_token.revoked = True
        db.commit()

def revoke_all_user_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()


# ==========================================
# 5. BUSINESS LOGIC (app/services/auth_service.py)
# ==========================================
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, data: RegisterRequest):
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
        role=data.role or "buyer",
        verification_token=verification_token,
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
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

def send_email_template(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Email '{subject}' sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email '{subject}' to {to_email}. Error: {e}")
        print(f"\n--- MOCK EMAIL [Subject: {subject}] ---")
        print(f"To: {to_email}")
        print(f"Content:\n{body}")
        print("------------------------------------------\n")

def send_verification_email(to_email: str, token: str):
    link = f"http://localhost:5500/index.html?token={token}"
    body = f"Please verify your email by clicking on the link:\n{link}\n\nThis link is valid for 24 hours."
    send_email_template(to_email, "Verify your ShopCore Account", body)

def send_reset_password_email(to_email: str, token: str):
    link = f"http://localhost:5500/index.html?reset_token={token}"
    body = f"You requested a password reset. Click the link to reset your password:\n{link}\n\nThis link is valid for 15 minutes. If you did not request this, ignore this email."
    send_email_template(to_email, "Reset your ShopCore Password", body)

def send_new_device_login_alert(to_email: str, ip_address: str):
    body = f"We detected a login to your account from a new IP address: {ip_address}.\n\nIf this was you, no action is needed. If this wasn't you, please secure your account by changing your password immediately."
    send_email_template(to_email, "Security Alert: Login from New Device/Location", body)

def send_lockout_alert_email(to_email: str):
    body = f"Your ShopCore account has been locked due to {MAX_LOGIN_ATTEMPTS} consecutive failed login attempts.\n\nPlease contact an administrator or request a password reset to unlock your account."
    send_email_template(to_email, "Security Alert: Account Locked", body)

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

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Security Dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token content"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
        
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    if user.is_locked:
        # Check if lockout duration has passed
        if user.locked_until:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            locked_until_naive = user.locked_until.replace(tzinfo=None) if user.locked_until.tzinfo else user.locked_until
            if locked_until_naive < now:
                # Auto unlock
                user.is_locked = False
                user.failed_login_attempts = 0
                user.locked_until = None
                db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is locked. Please unlock via email or admin."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked. Please unlock via email or admin."
            )
            
    return user

class RequireRole:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role must be one of {self.allowed_roles}"
            )
        return current_user

def verify_resource_ownership(current_user: User, owner_id: int):
    # Sellers can only modify their own resources, admins/superadmins can modify anything
    if current_user.role == "seller" and current_user.id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: sellers can only modify their own resources"
        )

# Routes
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

    if user.verification_token != token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is invalid or has already been used"
        )

    user.is_verified = True
    user.verification_token = None
    user.token_expires_at = None
    db.commit()
    db.refresh(user)
    return {"message": "Email verified successfully"}

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
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else "127.0.0.1"
    user = get_user_by_email(db, login_data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    # Check if locked
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.is_locked:
        if user.locked_until:
            locked_until_naive = user.locked_until.replace(tzinfo=None) if user.locked_until.tzinfo else user.locked_until
            if locked_until_naive < now:
                # Unlock automatically if duration passed
                user.is_locked = False
                user.failed_login_attempts = 0
                user.locked_until = None
                db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is locked. Please unlock via email or admin."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked. Please unlock via email or admin."
            )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Lockout tracking
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.is_locked = True
            user.locked_until = now + timedelta(minutes=15)
            db.commit()
            send_lockout_alert_email(str(user.email))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked due to {MAX_LOGIN_ATTEMPTS} failed attempts. Lock expires in 15 minutes."
            )
        else:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect email or password. Attempt {user.failed_login_attempts} of {MAX_LOGIN_ATTEMPTS}."
            )
            
    # Email verification check
    if REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified."
        )

    # Detect login from new device/location
    if user.last_login_ip and user.last_login_ip != ip_address:
        send_new_device_login_alert(str(user.email), ip_address)
        
    # Reset security fields
    user.failed_login_attempts = 0
    user.is_locked = False
    user.locked_until = None
    user.last_login_at = now
    user.last_login_ip = ip_address
    
    # Generate token pair
    access_token = create_access_token(str(user.email))
    refresh_token = create_refresh_token(db, user.id, ip_address)
    
    db.commit()
    db.refresh(user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )

@app.post("/auth/refresh", response_model=LoginResponse, tags=["Auth"])
def refresh(request: Request, refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else "127.0.0.1"
    new_access, new_refresh = rotate_refresh_token(db, refresh_data.refresh_token, ip_address)
    
    # Get user to return UserResponse
    db_token = db.query(RefreshToken).filter(RefreshToken.token == new_refresh).first()
    user = db.query(User).filter(User.id == db_token.user_id).first()
    
    return LoginResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=user
    )

@app.post("/auth/logout", tags=["Auth"])
def logout(refresh_data: TokenRefreshRequest, logout_everywhere: Optional[bool] = False, db: Session = Depends(get_db)):
    db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_data.refresh_token).first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    if logout_everywhere:
        revoke_all_user_tokens(db, db_token.user_id)
        return {"message": "Logged out from all sessions successfully"}
    else:
        revoke_refresh_token(db, refresh_data.refresh_token)
        return {"message": "Logged out successfully"}

@app.post("/auth/forgot-password", tags=["Auth"])
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    # Always return a success response to prevent email enumeration
    if user:
        reset_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = expires_at.replace(tzinfo=None)
        db.commit()
        
        send_reset_password_email(str(user.email), reset_token)
        
    return {"message": "If this email exists, a password reset link has been sent."}

@app.post("/auth/reset-password", tags=["Auth"])
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_naive = user.reset_token_expires_at.replace(tzinfo=None) if user.reset_token_expires_at.tzinfo else user.reset_token_expires_at
    if expires_naive < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
        
    # Update password and unlock user
    user.hashed_password = hash_password(request.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    user.failed_login_attempts = 0
    user.is_locked = False
    user.locked_until = None
    
    # Invalidate all active sessions (force re-login)
    revoke_all_user_tokens(db, user.id)
    db.commit()
    
    send_email_template(
        str(user.email),
        "ShopCore Password Changed",
        "Your password has been successfully reset. If you did not make this change, please contact support."
    )
    
    return {"message": "Password reset successfully. You can now log in."}

@app.post("/auth/change-password", tags=["Auth"])
def change_password(request: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
        
    # Set new password and invalidate other sessions
    current_user.hashed_password = hash_password(request.new_password)
    revoke_all_user_tokens(db, current_user.id)
    db.commit()
    
    return {"message": "Password changed successfully. All other sessions have been logged out."}

# Mock OAuth2 Google Endpoints
class OAuth2CallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None

@app.get("/auth/oauth/google", tags=["Auth"])
def google_auth_initiate():
    # Return mock consent flow page redirect (handled on frontend)
    mock_auth_url = "http://localhost:5500/index.html?provider=google&state=some-state"
    return {"auth_url": mock_auth_url}

@app.post("/auth/oauth/google/callback", response_model=LoginResponse, tags=["Auth"])
def google_auth_callback(request: Request, data: OAuth2CallbackRequest, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else "127.0.0.1"
    
    # For simulation: the code matches the user's mock email username
    email = data.code
    if "@" not in email:
        email = f"{data.code}@gmail.com"
        
    first_name = data.code.split("@")[0].capitalize()
    last_name = "GoogleUser"
    
    user = get_user_by_email(db, email)
    if not user:
        user = User(
            email=email,
            hashed_password=None,  # No password for OAuth users
            first_name=first_name,
            last_name=last_name,
            role="buyer",
            is_verified=True,  # Google verifies email
            created_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.last_login_at = now
    user.last_login_ip = ip_address
    
    access_token = create_access_token(str(user.email))
    refresh_token = create_refresh_token(db, user.id, ip_address)
    
    db.commit()
    db.refresh(user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )

# Admin & Role Restriction Protected Routes
@app.get("/admin/users", response_model=List[UserResponse], tags=["Admin"])
def list_users(current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/admin/users/{user_id}/lock", tags=["Admin"])
def lock_user(user_id: int, current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_locked = True
    user.locked_until = None  # Lock indefinitely until unlocked by admin
    revoke_all_user_tokens(db, user.id)
    db.commit()
    return {"message": f"User {user.email} has been locked."}

@app.post("/admin/users/{user_id}/unlock", tags=["Admin"])
def unlock_user(user_id: int, current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"message": f"User {user.email} has been unlocked."}

@app.get("/seller/dashboard", tags=["Seller"])
def seller_dashboard(current_user: User = Depends(RequireRole(["seller", "admin", "superadmin"]))):
    return {
        "message": "Welcome to the Seller Portal!",
        "role": current_user.role,
        "actions_allowed": ["create_listing", "update_listing"]
    }

@app.get("/seller/products/{owner_id}/modify", tags=["Seller"])
def seller_modify_resource(owner_id: int, current_user: User = Depends(RequireRole(["seller", "admin", "superadmin"]))):
    verify_resource_ownership(current_user, owner_id)
    return {"message": f"Authorization verification successful. You are allowed to edit resources owned by user #{owner_id}."}



# start the backend: uvicorn all_in_one:app --reload
# start the frontend: cd "d:\Backend Projects\shopcore\frontend"
# python -m http.server 5500
