from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from App.Database_Setup import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(String, default="buyer", nullable=False)  # "buyer", "seller"
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
