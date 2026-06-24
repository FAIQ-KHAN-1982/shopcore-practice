from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import RegisterRequest, UserResponse
from app.services.auth_service import create_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
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