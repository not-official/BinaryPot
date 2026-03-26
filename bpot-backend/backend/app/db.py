# app/db.py
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, String, DateTime, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./binarypot.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# ONE shared Base + Models
# ----------------------------
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SignupRequestDB(Base):
    __tablename__ = "signup_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/APPROVED/REJECTED

    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(500))

    organization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
