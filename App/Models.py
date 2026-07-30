from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from App.Database_Setup import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="buyer", nullable=False)  # "buyer", "seller"
    is_verified: Mapped[bool] = mapped_column(default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    # Login security fields
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(default=False, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Password reset fields
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    address_line_1: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)

