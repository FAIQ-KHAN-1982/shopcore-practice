from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "super-secret-key-change-this"
ALGORITHM = "HS256"

def create_verification_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)