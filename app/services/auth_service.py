from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.users import User
from app.security.hashing import hash_password
from app.security.tokens import create_verification_token


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