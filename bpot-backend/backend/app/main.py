# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import engine, Base
from .auth import router as auth_router
from .api import router as api_router
from .register import router as signup_router
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Honeypot API", version="0.2")

# Create tables on startup
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(signup_router)

@app.get("/")
def root():
    return {"status": "Binary-Pot backend running"}
