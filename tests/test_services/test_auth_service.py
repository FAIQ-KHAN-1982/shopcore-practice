import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from App.Database_Setup import Base
from App.Models import User
from App.Schemas import RegisterRequest, LoginRequest
from App.Services.auth_service import (
    get_user_by_email,
    create_user,
    login_user
)
from App.Security import MAX_LOGIN_ATTEMPTS

# Set up in-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.client.host = "127.0.0.1"
    return request


def test_get_user_by_email_found_and_not_found(db_session):
    # Not found
    assert get_user_by_email(db_session, "nonexistent@example.com") is None

    # Create user and test found
    register_data = RegisterRequest(
        email="test@example.com",
        password="Password123!",
        first_name="John",
        last_name="Doe",
        role="buyer"
    )
    user, _ = create_user(db_session, register_data)
    
    fetched_user = get_user_by_email(db_session, "test@example.com")
    assert fetched_user is not None
    assert fetched_user.id == user.id
    assert fetched_user.email == "test@example.com"


def test_create_user_success(db_session):
    register_data = RegisterRequest(
        email="newuser@example.com",
        password="SecurePassword1!",
        first_name="Alice",
        last_name="Smith",
        phone="1234567890",
        role="buyer"
    )
    user, token = create_user(db_session, register_data)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.first_name == "Alice"
    assert user.hashed_password != "SecurePassword1!"
    assert token is not None
    assert user.verification_token == token


def test_create_user_duplicate_email_raises_value_error(db_session):
    register_data = RegisterRequest(
        email="duplicate@example.com",
        password="Password123!",
        first_name="Jane",
        last_name="Doe",
        role="buyer"
    )
    create_user(db_session, register_data)

    with pytest.raises(ValueError, match="Email already exists"):
        create_user(db_session, register_data)


def test_login_user_nonexistent_user(db_session, mock_request):
    login_data = LoginRequest(email="nobody@example.com", password="Password123!")

    with pytest.raises(HTTPException) as exc_info:
        login_user(mock_request, login_data, db_session)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in exc_info.value.detail


def test_login_user_wrong_password_increments_failed_attempts(db_session, mock_request):
    register_data = RegisterRequest(
        email="user@example.com",
        password="Password123!",
        first_name="Test",
        last_name="User",
        role="buyer"
    )
    user, _ = create_user(db_session, register_data)
    user.is_verified = True
    db_session.commit()

    login_data = LoginRequest(email="user@example.com", password="WrongPassword123!")

    with pytest.raises(HTTPException) as exc_info:
        login_user(mock_request, login_data, db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    db_session.refresh(user)
    assert user.failed_login_attempts == 1


@patch("App.Services.auth_service.send_lockout_alert_email")
def test_login_user_exceed_max_attempts_locks_account(mock_lockout_email, db_session, mock_request):
    register_data = RegisterRequest(
        email="lockout@example.com",
        password="Password123!",
        first_name="Test",
        last_name="User",
        role="buyer"
    )
    user, _ = create_user(db_session, register_data)
    user.is_verified = True
    user.failed_login_attempts = MAX_LOGIN_ATTEMPTS - 1
    db_session.commit()

    login_data = LoginRequest(email="lockout@example.com", password="WrongPassword123!")

    with pytest.raises(HTTPException) as exc_info:
        login_user(mock_request, login_data, db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Account locked" in exc_info.value.detail

    db_session.refresh(user)
    assert user.is_locked is True
    assert user.locked_until is not None
    mock_lockout_email.assert_called_once_with("lockout@example.com")


def test_login_user_locked_account_before_and_after_expiration(db_session, mock_request):
    register_data = RegisterRequest(
        email="expiredlock@example.com",
        password="Password123!",
        first_name="Test",
        last_name="User",
        role="buyer"
    )
    user, _ = create_user(db_session, register_data)
    user.is_verified = True
    user.is_locked = True
    # Lock set to 5 minutes ago (expired)
    user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    db_session.commit()

    login_data = LoginRequest(email="expiredlock@example.com", password="Password123!")
    response = login_user(mock_request, login_data, db_session)

    assert response.access_token is not None
    db_session.refresh(user)
    assert user.is_locked is False
    assert user.failed_login_attempts == 0


@patch("App.Services.auth_service.send_new_device_login_alert")
def test_login_user_successful_login_and_new_device_alert(mock_device_alert, db_session, mock_request):
    register_data = RegisterRequest(
        email="success@example.com",
        password="Password123!",
        first_name="Success",
        last_name="User",
        role="buyer"
    )
    user, _ = create_user(db_session, register_data)
    user.is_verified = True
    user.last_login_ip = "192.168.1.1"  # Old IP
    db_session.commit()

    # Login from new IP "127.0.0.1"
    login_data = LoginRequest(email="success@example.com", password="Password123!")
    response = login_user(mock_request, login_data, db_session)

    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.user.email == "success@example.com"
    
    mock_device_alert.assert_called_once_with("success@example.com", "127.0.0.1")
