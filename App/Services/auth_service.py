from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from App.Models import User
from App.Schemas import RegisterRequest
from App.Security import hash_password, create_verification_token

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
