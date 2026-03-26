# logger.py
import json
import time
from pathlib import Path
from threading import Lock

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_conn_lock = Lock()
_cmd_lock = Lock()

def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def log_connection(remote_addr, username, password, event="connect", session_id: str = None, extra=None):
    """Log a connection/auth event.

    session_id: optional short id to correlate with command logs (written as top-level field).
    extra: optional dict for any additional metadata (merged into the entry, but session_id takes precedence).
    """
    entry = {
        "time": _now_iso(),
        "event": event,
        "remote_addr": remote_addr,
        "username": username,
        "password": password,
    }
    # session_id as top-level for easy querying
    if session_id:
        entry["session_id"] = session_id
    if extra:
        # do not overwrite explicit session_id passed as parameter
        extra_copy = dict(extra)
        if "session_id" in extra_copy and session_id:
            extra_copy.pop("session_id")
        entry.update(extra_copy)
    with _conn_lock:
        with open(LOG_DIR / "connections.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def log_command(remote_addr, username, command, session_id=None, output= None):
    entry = {
        "time": _now_iso(),
        "event": "command",
        "remote_addr": remote_addr,
        "username": username,
        "command": command,
        "output": output if output else "",
    }
    if session_id:
        entry["session_id"] = session_id
    with _cmd_lock:
        with open(LOG_DIR / "commands.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
