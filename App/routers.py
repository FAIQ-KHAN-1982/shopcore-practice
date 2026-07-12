from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import jwt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from App.Database_Setup import get_db
from App.Models import User, RefreshToken
from App.Schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    LoginResponse,
    TokenRefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    OAuth2CallbackRequest,
    resendingtoken,
    EmailStr
)
from App.Security import (
    SECRET_KEY,
    ALGORITHM,
    MAX_LOGIN_ATTEMPTS,
    REQUIRE_EMAIL_VERIFICATION,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user,
    RequireRole,
    verify_resource_ownership,
    create_verification_token
)
from App.Services import (
    get_user_by_email,
    create_user,
    send_verification_email,
    send_reset_password_email,
    send_new_device_login_alert,
    send_lockout_alert_email
)

router = APIRouter()

@router.get("/auth/verify", tags=["Auth"])
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

@router.post("/auth/register", response_model=UserResponse, status_code=201, tags=["Auth"])
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

@router.get("/auth/resend_verfication_token", tags=["Auth"])
def resend_verification_token_endpoint(email: EmailStr, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified"
        )
    verification_token = create_verification_token(str(user.email))
    user.verification_token = verification_token
    user.token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    db.commit()
    db.refresh(user)
    send_verification_email(str(user.email), verification_token)
    return {"message": "Verification token sent successfully"}


@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
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

@router.post("/auth/refresh", response_model=LoginResponse, tags=["Auth"])
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

@router.post("/auth/logout", tags=["Auth"])
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

@router.post("/auth/forgot-password", tags=["Auth"])
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

@router.post("/auth/reset-password", tags=["Auth"])
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

@router.post("/auth/change-password", tags=["Auth"])
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
@router.get("/auth/oauth/google", tags=["Auth"])
def google_auth_initiate():
    # Return mock consent flow page redirect (handled on frontend)
    mock_auth_url = "http://localhost:5500/index.html?provider=google&state=some-state"
    return {"auth_url": mock_auth_url}

@router.post("/auth/oauth/google/callback", response_model=LoginResponse, tags=["Auth"])
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
@router.get("/admin/users", response_model=List[UserResponse], tags=["Admin"])
def list_users(current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/admin/users/{user_id}/lock", tags=["Admin"])
def lock_user(user_id: int, current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_locked = True
    user.locked_until = None  # Lock indefinitely until unlocked by admin
    revoke_all_user_tokens(db, user.id)
    db.commit()
    return {"message": f"User {user.email} has been locked."}

@router.post("/admin/users/{user_id}/unlock", tags=["Admin"])
def unlock_user(user_id: int, current_user: User = Depends(RequireRole(["admin", "superadmin"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"message": f"User {user.email} has been unlocked."}

@router.get("/seller/dashboard", tags=["Seller"])
def seller_dashboard(current_user: User = Depends(RequireRole(["seller", "admin", "superadmin"]))):
    return {
        "message": "Welcome to the Seller Portal!",
        "role": current_user.role,
        "actions_allowed": ["create_listing", "update_listing"]
    }

@router.get("/seller/products/{owner_id}/modify", tags=["Seller"])
def seller_modify_resource(owner_id: int, current_user: User = Depends(RequireRole(["seller", "admin", "superadmin"]))):
    verify_resource_ownership(current_user, owner_id)
    return {"message": f"Authorization verification successful. You are allowed to edit resources owned by user #{owner_id}."}

