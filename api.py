from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
LOG_DIR = Path("logs")
CONN_FILE = LOG_DIR / "connections.jsonl"
CMD_FILE = LOG_DIR / "commands.jsonl"

app = FastAPI(title="Honeypot API", version="0.2")

# ----------------------------------------------------------------------
# Enable CORS for React frontend
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with ["http://localhost:3000"] for stricter setup
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def _read_jsonl(path: Path) -> List[dict]:
    """Read a .jsonl file and return a list of dicts, skipping malformed lines."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    out = []
    with path.open("r", encoding="utf8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
    return out


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse ISO or strptime timestamps."""
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None

# ----------------------------------------------------------------------
# API endpoints
# ----------------------------------------------------------------------

@app.get("/health")
def health():
    """Simple health check."""
    return {"status": "ok"}


@app.get("/connections")
def get_connections(
    limit: int = Query(500, ge=1, le=5000),
    username: Optional[str] = None,
    since: Optional[str] = None,
):
    """Return connection/auth events."""
    try:
        entries = _read_jsonl(CONN_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="connections log not found")

    # Optional filters
    if username:
        entries = [e for e in entries if e.get("username") == username]

    if since:
        dt = _parse_iso(since)
        if not dt:
            raise HTTPException(status_code=400, detail="invalid since timestamp")
        entries = [
            e for e in entries
            if _parse_iso(e.get("time", "")) and _parse_iso(e["time"]) >= dt
        ]

    # Most recent first
    return list(reversed(entries))[:limit]


@app.get("/commands")
def get_commands(
    limit: int = Query(500, ge=1, le=5000),
    username: Optional[str] = None,
    since: Optional[str] = None,
):
    """Return recorded commands."""
    try:
        entries = _read_jsonl(CMD_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="commands log not found")

    # Optional filters
    if username:
        entries = [e for e in entries if e.get("username") == username]

    if since:
        dt = _parse_iso(since)
        if not dt:
            raise HTTPException(status_code=400, detail="invalid since timestamp")
        entries = [
            e for e in entries
            if _parse_iso(e.get("time", "")) and _parse_iso(e["time"]) >= dt
        ]

    # Most recent first
    return list(reversed(entries))[:limit]


@app.get("/sessions")
def get_sessions():
    """Group commands by session_id with all related activities."""
    try:
        entries = _read_jsonl(CMD_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="commands log not found")

    sessions = {}
    for e in entries:
        sid = e.get("session_id")
        if not sid:
            continue
        sessions.setdefault(sid, []).append({
            "time": e.get("time"),
            "command": e.get("command"),
            "username": e.get("username"),
            "remote_addr": e.get("remote_addr"),
        })

    # Sort activities by time
    for sid in sessions:
        sessions[sid].sort(key=lambda x: x.get("time", ""))

    return [
        {"session_id": sid, "activities": acts}
        for sid, acts in sessions.items()
    ]


@app.get("/raw/{log_name}")
def get_raw(log_name: str):
    """Return raw log file contents (commands or connections)."""
    if log_name == "connections":
        path = CONN_FILE
    elif log_name == "commands":
        path = CMD_FILE
    else:
        raise HTTPException(status_code=404, detail="unknown log")

    if not path.exists():
        raise HTTPException(status_code=404, detail="log not found")

    return {"path": str(path), "content": path.read_text(encoding="utf8")}

@app.get("/sessions/{session_id}/commands")
def get_commands_for_session(session_id: str, limit: int = Query(500, ge=1, le=5000)):
    """Return up to `limit` most recent commands for the given session_id."""
    try:
        entries = _read_jsonl(CMD_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="commands log not found")

    matched = [e for e in entries if e.get("session_id") == session_id]
    # most recent first
    return list(reversed(matched))[:limit]
