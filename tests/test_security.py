import pytest
from App.Security import hash_password, verify_password, create_access_token
import jwt
from App.Security import SECRET_KEY, ALGORITHM

def test_hash_password_returns_different_string():
    """Test that password hashing does not return the plain password."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert isinstance(hashed, str)

def test_verify_password_correct():
    """Test that verify_password returns True for matching password."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True

def test_verify_password_wrong_password():
    """Test that verify_password returns False for non-matching password."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password("WrongPassword123!", hashed) is False

def test_create_access_token():
    """Test that create_access_token returns a valid JWT with subject claim."""
    email = "testuser@example.com"
    token = create_access_token(email)
    
    assert isinstance(token, str)
    
    # Decode the token to verify claims
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == email
    assert "exp" in decoded
