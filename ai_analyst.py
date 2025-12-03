import json
import collections
from pathlib import Path
import gaiservices # Reuse your existing connection!

LOG_FILE = Path("logs/commands.jsonl")

async def analyze_latest_session():
    # 1. Read the logs
    if not LOG_FILE.exists():
        print("No logs found.")
        return

    sessions = collections.defaultdict(list)
    
    # Group commands by Session ID
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                sid = entry.get('session_id', 'unknown')
                sessions[sid].append(entry)
            except:
                continue

    # Get the most recent session (last one in the file)
    # In a real tool, you might list them all.
    last_session_id = list(sessions.keys())[-1]
    session_data = sessions[last_session_id]

    print(f"Analyzing Session: {last_session_id} ({len(session_data)} commands)")

    # 2. Build the Transcript
    transcript = "SESSION TRANSCRIPT:\n"
    for event in session_data:
        transcript += f"Attacker: {event['command']}\n"
        transcript += f"Honeypot: {event['output'][:200]}...\n" # Truncate long outputs
        transcript += "---\n"

    # 3. Ask the AI Detective
    system_prompt = (
        "You are a Cybersecurity Analyst. "
        "Review this SSH honeypot session logs. "
        "Identify the attacker's intent (e.g., bot, human, script kiddie). "
        "Did they succeed in finding anything interesting? "
        "Summarize the attack in 3 bullet points."
    )

    print("\n--- Generating AI Report ---\n")
    report = await gaiservices.get_ai_response(transcript, system_prompt)
    
    print(report)

# Wrapper to run it
if __name__ == "__main__":
    import asyncio
    asyncio.run(analyze_latest_session())