# command_to_session_converter.py
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path




BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"


INPUT_FILE = LOGS_DIR / "commands.jsonl"
OUTPUT_FILE = LOGS_DIR / "sessions_clean.json"




def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.min




def load_existing_sessions():
    if not OUTPUT_FILE.exists():
        return []


    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)


        if isinstance(data, list):
            return data


        return []


    except json.JSONDecodeError:
        return []




def convert_commands_to_sessions():
    LOGS_DIR.mkdir(exist_ok=True)


    if not INPUT_FILE.exists():
        print(f"No command log found at {INPUT_FILE}")
        return {
            "new_sessions": 0,
            "total_sessions": 0,
            "output_file": str(OUTPUT_FILE),
        }


    sessions = defaultdict(list)


    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()


            if not line:
                continue


            try:
                log = json.loads(line)
            except json.JSONDecodeError:
                continue


            session_id = log.get("session_id")


            if not session_id:
                continue


            sessions[session_id].append({
                "time": log.get("time", ""),
                "event": log.get("event", "command"),
                "remote_addr": log.get("remote_addr", "unknown"),
                "username": log.get("username", "unknown"),
                "command": log.get("command", ""),
                "output": log.get("output", ""),
                "cwd": log.get("cwd", ""),
                "command_index": log.get("command_index"),
            })


    existing_sessions = load_existing_sessions()
    existing_session_ids = {s.get("session_id") for s in existing_sessions}


    new_sessions = []


    for session_id, logs in sessions.items():
        if session_id in existing_session_ids:
            continue


        logs.sort(
            key=lambda x: (
                x["command_index"] if x["command_index"] is not None else 999999,
                parse_time(x["time"]),
            )
        )


        first_log = logs[0] if logs else {}


        commands = []


        for entry in logs:
            commands.append({
                "command": entry["command"],
                "cwd": entry["cwd"],
            })


        new_sessions.append({
            "session_id": session_id,
            "command_count": len(commands),
            "commands": commands,
        })


    all_sessions = existing_sessions + new_sessions


    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_sessions, f, indent=4, ensure_ascii=False)


    print(f"{len(new_sessions)} new sessions added.")
    print(f"Total sessions: {len(all_sessions)}")
    print(f"Saved to {OUTPUT_FILE}")


    return {
        "new_sessions": len(new_sessions),
        "total_sessions": len(all_sessions),
        "output_file": str(OUTPUT_FILE),
    }




if __name__ == "__main__":
    convert_commands_to_sessions()



