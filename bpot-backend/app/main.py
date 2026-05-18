# app/main.py
import json
import subprocess
import sys
from pathlib import Path
from typing import Union

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


from .db import engine, Base
from .auth import router as auth_router
from .api import router as api_router
from .register import router as signup_router

from .geoip import router as geoip_router


# ============================================================
# BASE PATH SETUP
# ============================================================





LOGS_DIR = BASE_DIR / "logs"


SESSION_FILE = LOGS_DIR / "sessions_clean.json"
ANALYSIS_FILE = LOGS_DIR / "session_commands_with_intent.json"


CONVERTER_SCRIPT = BASE_DIR / "command_to_session_converter.py"




# ============================================================
# FASTAPI APP
# ============================================================


app = FastAPI(title="Honeypot API", version="0.2")




# ============================================================
# DATABASE SETUP
# ============================================================


Base.metadata.create_all(bind=engine)




# ============================================================
# CORS
# ============================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# ============================================================
# ROUTERS
# ============================================================


app.include_router(auth_router)
app.include_router(api_router)
app.include_router(signup_router)
app.include_router(
    geoip_router,
    prefix="/api/geoip",
    tags=["GeoIP"]
)





# ============================================================
# FILE HELPERS
# ============================================================


def load_file(file_path: Path) -> Union[list, dict]:
    try:
        if file_path.suffix == ".jsonl":
            with file_path.open("r", encoding="utf-8") as file:
                return [
                    json.loads(line)
                    for line in file
                    if line.strip()
                ]


        if file_path.suffix == ".json":
            with file_path.open("r", encoding="utf-8") as file:
                return json.load(file)


        raise HTTPException(
            status_code=400,
            detail="Only .json and .jsonl files are supported",
        )


    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON file: {e}",
        )


    except IOError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {e}",
        )




# ============================================================
# SESSION CONVERTER
# ============================================================


def run_converter():
    """
    Converts logs/commands.jsonl into logs/sessions_clean.json.
    """


    try:
        if not CONVERTER_SCRIPT.exists():
            print(f"Converter script not found: {CONVERTER_SCRIPT}")
            return


        subprocess.run(
            [sys.executable, str(CONVERTER_SCRIPT)],
            cwd=str(BASE_DIR),
            check=True,
        )


        print("Converter executed successfully")


    except subprocess.CalledProcessError as e:
        print(f"Converter failed: {e}")


    except Exception as e:
        print(f"Converter error: {e}")




# ============================================================
# BEHAVIOR ANALYSIS
# ============================================================


def run_behavior_analysis():
    """
    Runs ai/behavior_engine.py logic.


    Reads:
        logs/sessions_clean.json


    Writes:
        logs/session_commands_with_intent.json
    """


    try:
        from ai.behavior_engine import analyze_sessions


        if not SESSION_FILE.exists():
            print("sessions_clean.json not found. Skipping behavior analysis.")
            return


        LOGS_DIR.mkdir(parents=True, exist_ok=True)


        result = analyze_sessions(
            input_file=SESSION_FILE,
            output_file=ANALYSIS_FILE,
        )


        print("Behavior analysis completed:", result)


    except Exception as e:
        print(f"Behavior analysis failed: {e}")




def run_pipeline():
    """
    Full preprocessing pipeline:
    1. Convert command logs to clean sessions
    2. Analyze sessions using DistilBERT, BART, and Cerebras summary
    """


    print("Running BinaryPot preprocessing pipeline...")


    run_converter()
    run_behavior_analysis()


    print("Pipeline completed.")




# ============================================================
# ROOT ENDPOINT
# ============================================================


@app.get("/")
def root():
    available_logs = []


    if LOGS_DIR.exists():
        available_logs = [
            file.name
            for file in LOGS_DIR.iterdir()
            if file.suffix in {".json", ".jsonl"}
        ]


    return {
        "status": "Binary-Pot backend running",
        "logs": available_logs,
        "important_endpoints": {
            "sessions_clean": "/logs/sessions_clean",
            "analysis_results": "/analysis/results",
            "manual_analysis": "/analysis/run",
            "log_file_reader": "/logs/file/{file_name}",
        },
    }




# ============================================================
# SESSION START / END ENDPOINTS
# Called from honeypot/ssh_server.py
# ============================================================


@app.post("/session/start")
def session_start(data: dict, background_tasks: BackgroundTasks):
    print("SESSION START:", data)


    # Only convert logs on start.
    # Heavy behavior analysis is NOT run here.
    background_tasks.add_task(run_converter)


    return {
        "status": "started",
        "session_id": data.get("session_id"),
    }




@app.post("/session/end")
def session_end(data: dict, background_tasks: BackgroundTasks):
    print("SESSION END:", data)


    # Run full pipeline only when the SSH session ends.
    background_tasks.add_task(run_pipeline)


    return {
        "status": "ended",
        "session_id": data.get("session_id"),
    }




# ============================================================
# CLEAN SESSION LOGS
# ============================================================


@app.get("/logs/sessions_clean")
def get_sessions_clean():
    if not SESSION_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="sessions_clean.json not found",
        )


    return JSONResponse(content=load_file(SESSION_FILE))




# ============================================================
# BEHAVIOR ANALYSIS ENDPOINTS
# ============================================================


@app.post("/analysis/run")
def run_analysis(background_tasks: BackgroundTasks):
    """
    Manually trigger:
    commands.jsonl -> sessions_clean.json -> session_commands_with_intent.json
    """


    background_tasks.add_task(run_pipeline)


    return {
        "status": "analysis_started",
        "output_file": str(ANALYSIS_FILE),
    }




@app.get("/analysis/results")
def get_analysis_results():
    if not ANALYSIS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="session_commands_with_intent.json not found. Run /analysis/run first.",
        )


    return JSONResponse(content=load_file(ANALYSIS_FILE))




# ============================================================
# DYNAMIC LOG FILE ENDPOINT
# Example:
# /logs/file/commands.jsonl
# /logs/file/connections.jsonl
# /logs/file/sessions_clean.json
# /logs/file/session_commands_with_intent.json
# ============================================================


@app.get("/logs/file/{file_name}")
def get_log_file(file_name: str):
    file_path = LOGS_DIR / file_name


    if file_path.exists() and file_path.is_file():
        return JSONResponse(content=load_file(file_path))


    raise HTTPException(
        status_code=404,
        detail="Log file not found",
    )




# ============================================================
# LIST AVAILABLE LOG FILES
# ============================================================


@app.get("/files")
def list_available_files():
    logs = []


    if LOGS_DIR.exists():
        logs = [
            file.name
            for file in LOGS_DIR.iterdir()
            if file.suffix in {".json", ".jsonl"}
        ]


    return {
        "logs": logs,
    }



