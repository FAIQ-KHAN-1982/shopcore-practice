import os
from datetime import datetime, timedelta, timezone
import secrets
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from dotenv import load_dotenv
import App.Schemas

load_dotenv()

from App.Database_Setup import get_db
from App.Models import User, RefreshToken

# -- Configurable Security Constants --
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "True").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-insecure-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

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

# Security Dependencies
security_scheme = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials if credentials else None
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
        
    # Direct database query to avoid circular dependency with Services
    user = db.query(User).filter(User.email == email).first()
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


def RoleChecker(allowed_roles: list[str]):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user
    return role_dependency