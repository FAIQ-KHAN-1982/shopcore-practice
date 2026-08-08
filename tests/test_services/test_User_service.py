import pytest
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from App.Database_Setup import Base
from App.Models import User, Address
from App.Schemas import FieldsForAddress
from App.Services.User_service import (
    add_address,
    show_my_address,
    delete_address_by_id,
    update_address_by_id,
    default_address
)

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
def sample_user(db_session):
    user = User(
        email="testuser@example.com",
        hashed_password="hashed_pwd_123",
        first_name="Jane",
        last_name="Doe",
        phone="1234567890",
        role="buyer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def other_user(db_session):
    user = User(
        email="otheruser@example.com",
        hashed_password="hashed_pwd_456",
        first_name="Other",
        last_name="User",
        phone="0987654321",
        role="buyer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_add_address_success(db_session, sample_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )

    created_address = add_address(address_data, sample_user.id, db_session)

    assert created_address.id is not None
    assert created_address.user_id == sample_user.id
    assert created_address.full_name == "Jane Doe"
    assert created_address.address_line_1 == "123 Main St"
    assert created_address.city == "Metropolis"
    assert created_address.default is False


def test_show_my_address_success(db_session, sample_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )
    add_address(address_data, sample_user.id, db_session)

    addresses = show_my_address(sample_user, db_session)

    assert len(addresses) == 1
    assert addresses[0]["Name"] == "Jane Doe"
    assert addresses[0]["address"] == "123 Main St"
    assert addresses[0]["phone"] == "1234567890"
    assert addresses[0]["city"] == "Metropolis"


def test_delete_address_by_id_success(db_session, sample_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )
    addr = add_address(address_data, sample_user.id, db_session)

    delete_address_by_id(addr.id, sample_user, db_session)

    existing = db_session.query(Address).filter(Address.id == addr.id).first()
    assert existing is None


def test_delete_address_by_id_not_found_or_unauthorized(db_session, sample_user, other_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )
    addr = add_address(address_data, sample_user.id, db_session)

    # Non-existent address ID
    with pytest.raises(HTTPException) as exc_info:
        delete_address_by_id(9999, sample_user, db_session)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Address owned by sample_user, but attempted delete by other_user
    with pytest.raises(HTTPException) as exc_info:
        delete_address_by_id(addr.id, other_user, db_session)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_update_address_by_id_success(db_session, sample_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Old St",
        city="Old City"
    )
    addr = add_address(address_data, sample_user.id, db_session)

    update_data = FieldsForAddress(
        full_name="Jane Smith",
        phone="9998887777",
        address_line_1="456 New Ave",
        city="New City"
    )

    updated_addr = update_address_by_id(update_data, addr.id, sample_user, db_session)

    assert updated_addr.full_name == "Jane Smith"
    assert updated_addr.phone == "9998887777"
    assert updated_addr.address_line_1 == "456 New Ave"
    assert updated_addr.city == "New City"


def test_update_address_by_id_not_found(db_session, sample_user):
    update_data = FieldsForAddress(
        full_name="Jane Smith",
        phone="9998887777",
        address_line_1="456 New Ave",
        city="New City"
    )

    with pytest.raises(HTTPException) as exc_info:
        update_address_by_id(update_data, 9999, sample_user, db_session)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_default_address_success(db_session, sample_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )
    addr = add_address(address_data, sample_user.id, db_session)
    assert addr.default is False

    updated_addr = default_address(addr.id, sample_user, db_session)

    assert updated_addr.default is True


def test_default_address_not_found_or_unauthorized(db_session, sample_user, other_user):
    address_data = FieldsForAddress(
        full_name="Jane Doe",
        phone="1234567890",
        address_line_1="123 Main St",
        city="Metropolis"
    )
    addr = add_address(address_data, sample_user.id, db_session)

    # Non-existent ID
    with pytest.raises(HTTPException) as exc_info:
        default_address(9999, sample_user, db_session)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Address owned by sample_user, but set as default by other_user
    with pytest.raises(HTTPException) as exc_info:
        default_address(addr.id, other_user, db_session)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
