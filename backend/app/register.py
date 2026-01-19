# app/register.py
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from .db import get_db, User, SignupRequestDB
from .email_utils import send_signup_email

router = APIRouter(tags=["Signup"])

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
REQUEST_EXPIRE_HOURS = int(os.getenv("REQUEST_EXPIRE_HOURS", "48"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SignupRequestIn(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    terms: bool

    organization: Optional[str] = None
    role: Optional[str] = None
    usage: Optional[str] = None
    plan: Optional[str] = None

    # demo fields (not stored)
    card_name: Optional[str] = None
    card_number: Optional[str] = None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def is_expired(req: SignupRequestDB) -> bool:
    return datetime.utcnow() > req.expires_at

@router.post("/signup-request")
def signup_request(data: SignupRequestIn, db: Session = Depends(get_db)):
    if not data.terms:
        raise HTTPException(status_code=400, detail="Terms not accepted")

    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email = data.email.strip().lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="User already exists")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=REQUEST_EXPIRE_HOURS)

    req = SignupRequestDB(
        token=token,
        status="PENDING",
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        organization=data.organization,
        role=data.role,
        usage=data.usage,
        plan=data.plan,
        expires_at=expires_at,
    )
    db.add(req)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A signup request already exists")

    approve_url = f"{APP_BASE_URL}/signup-approve/{token}"
    reject_url = f"{APP_BASE_URL}/signup-reject/{token}"

    send_signup_email(
        payload={
            "full_name": data.full_name,
            "email": email,
            "organization": data.organization,
            "role": data.role,
            "usage": data.usage,
            "plan": data.plan,
        },
        approve_url=approve_url,
        reject_url=reject_url,
    )

    return {"message": "Signup request submitted for approval"}

@router.get("/signup-approve/{token}", response_class=HTMLResponse)
def signup_approve(token: str, db: Session = Depends(get_db)):
    req = db.query(SignupRequestDB).filter(SignupRequestDB.token == token).first()
    if not req:
        return HTMLResponse("<h3>Invalid approval link.</h3>", status_code=404)

    if req.status != "PENDING":
        return HTMLResponse(f"<h3>Request already {req.status}.</h3>", status_code=400)

    if is_expired(req):
        req.status = "REJECTED"
        db.commit()
        return HTMLResponse("<h3>Request expired and was rejected.</h3>", status_code=400)

    user = User(
        email=req.email,
        full_name=req.full_name,
        password_hash=req.password_hash,
        is_active=True,
        organization=req.organization,
        role=req.role,
        usage=req.usage,
        plan=req.plan,
    )
    db.add(user)
    req.status = "APPROVED"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return HTMLResponse("<h3>User already exists. Nothing to approve.</h3>", status_code=409)

    return HTMLResponse("<h2>Approved ✅ User account created and activated.</h2>")

@router.get("/signup-reject/{token}", response_class=HTMLResponse)
def signup_reject(token: str, db: Session = Depends(get_db)):
    req = db.query(SignupRequestDB).filter(SignupRequestDB.token == token).first()
    if not req:
        return HTMLResponse("<h3>Invalid reject link.</h3>", status_code=404)

    if req.status != "PENDING":
        return HTMLResponse(f"<h3>Request already {req.status}.</h3>", status_code=400)

    req.status = "REJECTED"
    db.commit()
    return HTMLResponse("<h2>Rejected ✅ Signup request has been rejected.</h2>")
