from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from App.Models import User
from App.Schemas import RegisterRequest, LoginRequest, LoginResponse, TokenRefreshRequest
from App.Security import hash_password, create_verification_token, verify_password, create_access_token, create_refresh_token, rotate_refresh_token, MAX_LOGIN_ATTEMPTS, REQUIRE_EMAIL_VERIFICATION
from App.Services.email_service import send_new_device_login_alert, send_lockout_alert_email

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


def login_user(request: Request, login_data: LoginRequest, db: Session):
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
