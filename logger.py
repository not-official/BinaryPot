# logger.py
import json
import time
from pathlib import Path
from threading import Lock

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_conn_lock = Lock()
_cmd_lock = Lock()

def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def log_connection(remote_addr, username, password, event="connect", extra=None):
    entry = {
        "time": _now_iso(),
        "event": event,
        "remote_addr": remote_addr,
        "username": username,
        "password": password,
    }
    if extra:
        entry.update(extra)
    with _conn_lock:
        with open(LOG_DIR / "connections.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def log_command(remote_addr, username, command, session_id=None):
    entry = {
        "time": _now_iso(),
        "event": "command",
        "remote_addr": remote_addr,
        "username": username,
        "command": command,
        "output": "",  # Placeholder for output capture
    }
    if session_id:
        entry["session_id"] = session_id
    with _cmd_lock:
        with open(LOG_DIR / "commands.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
