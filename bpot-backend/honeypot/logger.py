# logger.py
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock




LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)




_conn_lock = Lock()
_cmd_lock = Lock()




def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")




def log_connection(remote_addr, username, password, event="connect", session_id: str = None, extra=None):
    """Log a connection/auth event.


    session_id: optional short id to correlate with command logs.
    extra: optional dict for additional metadata.
    """


    entry = {
        "time": _now_iso(),
        "event": event,
        "remote_addr": remote_addr,
        "username": username or "unknown",
        "password": password or "",
    }


    if session_id:
        entry["session_id"] = session_id


    if extra:
        extra_copy = dict(extra)


        # Do not overwrite explicit session_id
        if "session_id" in extra_copy and session_id:
            extra_copy.pop("session_id")


        entry.update(extra_copy)


    with _conn_lock:
        with open(LOG_DIR / "connections.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")




def log_command(
    remote_addr,
    username,
    command,
    session_id=None,
    output=None,
    cwd=None,
    command_index=None
):
    """Log a command executed inside the honeypot session."""


    entry = {
        "time": _now_iso(),
        "event": "command",
        "remote_addr": remote_addr,
        "username": username or "unknown",
        "command": command,
        "output": output or "",
    }


    if session_id:
        entry["session_id"] = session_id


    if cwd:
        entry["cwd"] = cwd


    if command_index is not None:
        entry["command_index"] = command_index


    with _cmd_lock:
        with open(LOG_DIR / "commands.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

