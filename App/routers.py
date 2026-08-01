
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import jwt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from App.Services.User_service import add_address
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
    ResendVerificationTokenRequest,
    UpdateProfileRequest,
    FieldsForAddress
)
from App.Security import (
    SECRET_KEY,
    ALGORITHM,
    hash_password,
    verify_password,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user,
    create_verification_token
)
from App.Services import (
    get_user_by_email,
    create_user,
    send_verification_email,
    send_reset_password_email,
    login_user,
    send_email_template
)

router = APIRouter()

# ==================== AUTH ROUTES ====================

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
        background_tasks.add_task(send_verification_email, new_user.email, token)
        return new_user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/resend_verfication_token", tags=["Auth"])
def resend_verification_token_endpoint(data: ResendVerificationTokenRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)
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
    verification_token = create_verification_token(user.email)
    user.verification_token = verification_token
    user.token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    db.commit()
    db.refresh(user)
    send_verification_email(user.email, verification_token)
    return {"message": "Verification token sent successfully"}


@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    return login_user(request, login_data, db)

@router.post("/auth/refresh", response_model=LoginResponse, tags=["Auth"])
def refresh(request: Request, refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else "127.0.0.1"
    new_access, new_refresh = rotate_refresh_token(db, refresh_data.refresh_token, ip_address)
    
    # Get user to return UserResponse
    db_token = db.query(RefreshToken).filter(RefreshToken.token == new_refresh).first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return LoginResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=UserResponse.model_validate(user)
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
        
        send_reset_password_email(user.email, reset_token)
        
    return {"message": "If this email exists, a password reset link has been sent."}

@router.post("/auth/reset-password", tags=["Auth"])
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    
    if not user or user.reset_token_expires_at is None:
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
    
    send_email_template(user.email, "ShopCore Password Changed", "Your password has been successfully reset. If you did not make this change, please contact support.")
    
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


# ==================== USER MANAGMENT ROUTES ====================

@router.get("/users/me", tags=["User"])
def my_profile(current_user: User = Depends(get_current_user)):
    return {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
    }


@router.put("/users/me", response_model=UserResponse, tags=["User"])
def update_profile(data: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.first_name:
        current_user.first_name = data.first_name
    if data.last_name:
        current_user.last_name = data.last_name
    if data.phone:
        current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/users/me", tags=["User"]) # adding feature of deleting everything related to a user (i.e address, refresh_token)
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}

@router.post("/users/me/add_address", tags=["User"])
def address_adding(data: FieldsForAddress, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    add_address(data, current_user.id, db)
    return {"message": "Address added successfully"}









 
    






