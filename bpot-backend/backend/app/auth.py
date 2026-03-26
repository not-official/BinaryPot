# app/auth.py
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .db import get_db
from .register import User  # SQLAlchemy User model

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --------------------
# CONFIG (.env)
# --------------------
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_ENV")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --------------------
# Schemas
# --------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --------------------
# Helpers
# --------------------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(sub: str, role: str = "admin") -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": sub,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --------------------
# Routes
# --------------------
@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(sub=user.email, role="admin")

    return {
        "access_token": token,
        "token_type": "bearer",
    }
