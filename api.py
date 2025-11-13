from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query

LOG_DIR = Path("logs")
CONN_FILE = LOG_DIR / "connections.jsonl"
CMD_FILE = LOG_DIR / "commands.jsonl"

app = FastAPI(title="Honeypot API", version="0.1")

def _read_jsonl(path: Path) -> List[dict]:
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
                # skip malformed lines
                continue
    return out


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        # Expect format like 2025-10-18T12:34:56+0000
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/connections")
def get_connections(limit: int = Query(500, ge=1, le=5000), username: Optional[str] = None, since: Optional[str] = None):
    """Return connection/auth events. Optional filters: username, since (ISO timestamp)."""
    try:
        entries = _read_jsonl(CONN_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="connections log not found")

    if username:
        entries = [e for e in entries if e.get("username") == username]

    if since:
        dt = _parse_iso(since)
        if not dt:
            raise HTTPException(status_code=400, detail="invalid since timestamp")
        entries = [e for e in entries if _parse_iso(e.get("time", "")) and _parse_iso(e.get("time")) >= dt]

    # return most recent first
    return list(reversed(entries))[:limit]


@app.get("/commands")
def get_commands(limit: int = Query(500, ge=1, le=5000), username: Optional[str] = None, since: Optional[str] = None):
    """Return recorded commands. Optional filters: username, since (ISO timestamp)."""
    try:
        entries = _read_jsonl(CMD_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="commands log not found")

    if username:
        entries = [e for e in entries if e.get("username") == username]

    if since:
        dt = _parse_iso(since)
        if not dt:
            raise HTTPException(status_code=400, detail="invalid since timestamp")
        entries = [e for e in entries if _parse_iso(e.get("time", "")) and _parse_iso(e.get("time")) >= dt]

    # return most recent first
    return list(reversed(entries))[:limit]


@app.get("/raw/{log_name}")
def get_raw(log_name: str):
    """Download raw log file contents. Allowed: 'connections' or 'commands'"""
    if log_name == "connections":
        path = CONN_FILE
    elif log_name == "commands":
        path = CMD_FILE
    else:
        raise HTTPException(status_code=404, detail="unknown log")
    if not path.exists():
        raise HTTPException(status_code=404, detail="log not found")
    return {"path": str(path), "content": path.read_text(encoding="utf8")}
