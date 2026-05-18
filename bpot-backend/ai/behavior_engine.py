# ai/behavior_engine.py
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


import joblib
import torch
from dotenv import load_dotenv
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    BartTokenizerFast,
    BartForConditionalGeneration,
)


try:
    from cerebras.cloud.sdk import Cerebras
except Exception:
    Cerebras = None




# ============================================================
# PATH SETUP
# ============================================================


BASE_DIR = Path(__file__).resolve().parents[1]


MODELS_DIR = BASE_DIR / "models"
DISTILBERT_MODEL_PATH = MODELS_DIR / "distilbert"
BART_MODEL_PATH = MODELS_DIR / "bart"


LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"


INPUT_FILE = LOGS_DIR / "sessions_clean.json"
OUTPUT_FILE = DATA_DIR / "session_commands_with_intent.json"


ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)




# ============================================================
# GLOBAL MODEL CACHE
# ============================================================


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


_intent_tokenizer = None
_intent_model = None
_label_encoder = None


_desc_tokenizer = None
_desc_model = None


_cerebras_client = None
_models_loaded = False




# ============================================================
# MODEL LOADING
# ============================================================


def load_behavior_models():
    """
    Loads DistilBERT, BART, label encoder, and optional Cerebras client.
    Models are cached globally after first load.
    """


    global _intent_tokenizer
    global _intent_model
    global _label_encoder
    global _desc_tokenizer
    global _desc_model
    global _cerebras_client
    global _models_loaded


    if _models_loaded:
        return


    print("[BehaviorEngine] Loading behavioral analysis models...")
    print(f"[BehaviorEngine] Device: {device}")


    if not DISTILBERT_MODEL_PATH.exists():
        raise FileNotFoundError(f"DistilBERT model folder not found: {DISTILBERT_MODEL_PATH}")


    if not BART_MODEL_PATH.exists():
        raise FileNotFoundError(f"BART model folder not found: {BART_MODEL_PATH}")


    label_encoder_path = DISTILBERT_MODEL_PATH / "label_encoder.joblib"


    if not label_encoder_path.exists():
        raise FileNotFoundError(f"Label encoder not found: {label_encoder_path}")


    _intent_tokenizer = DistilBertTokenizerFast.from_pretrained(str(DISTILBERT_MODEL_PATH))
    _intent_model = DistilBertForSequenceClassification.from_pretrained(
        str(DISTILBERT_MODEL_PATH)
    ).to(device)
    _intent_model.eval()


    _label_encoder = joblib.load(str(label_encoder_path))


    _desc_tokenizer = BartTokenizerFast.from_pretrained(str(BART_MODEL_PATH))
    _desc_model = BartForConditionalGeneration.from_pretrained(
        str(BART_MODEL_PATH)
    ).to(device)
    _desc_model.eval()


    api_key = os.environ.get("CEREBRAS_API_KEY")


    if Cerebras is not None and api_key:
        try:
            _cerebras_client = Cerebras(api_key=api_key)
            print("[BehaviorEngine] Cerebras client ready.")
        except Exception as e:
            print(f"[BehaviorEngine] Cerebras client failed: {e}")
            _cerebras_client = None
    else:
        _cerebras_client = None
        print("[BehaviorEngine] Cerebras disabled or API key missing.")


    _models_loaded = True
    print("[BehaviorEngine] Behavioral analysis models loaded.")




# ============================================================
# INTENT PREDICTION
# ============================================================


def predict_intent(command: str) -> str:
    load_behavior_models()


    command = command or ""


    inputs = _intent_tokenizer(
        command,
        return_tensors="pt",
        truncation=True,
        padding=True,
    ).to(device)


    with torch.no_grad():
        outputs = _intent_model(**inputs)


    pred_id = torch.argmax(outputs.logits, dim=1).item()


    return _label_encoder.inverse_transform([pred_id])[0]




# ============================================================
# DESCRIPTION GENERATION
# ============================================================


def generate_description(command: str, intent: str, cwd: str = "") -> str:
    load_behavior_models()


    command = (command or "").strip()
    cwd = cwd or "/"


    # Simple rule-based descriptions for common shell movement commands
    if command == "ls":
        return f"Lists files and directories in {cwd}."


    if command in ("ls -la", "ls -al", "ls -l"):
        return f"Lists files and directories in {cwd} with detailed metadata."


    if command == "pwd":
        return f"Displays the current working directory, which is {cwd}."


    if command == "cd ..":
        parent = os.path.dirname(cwd.rstrip("/")) or "/"
        return f"Moves from {cwd} to the parent directory {parent}."


    if command.startswith("cd "):
        target = command.replace("cd ", "", 1).strip()
        return f"Changes the working directory from {cwd} to {target}."


    if command.startswith("cat "):
        target = command.replace("cat ", "", 1).strip()
        return f"Reads and displays the contents of {target} from the current shell context."


    if command.startswith("wget "):
        return "Attempts to download a remote file using wget, which may indicate payload retrieval or reconnaissance."


    if command.startswith("curl "):
        return "Uses curl to make a network request, often used for testing connectivity, downloading files, or probing services."


    if command.startswith("git clone"):
        return "Attempts to clone a remote Git repository into the current filesystem."


    # BART fallback
    prompt = (
        "You are a cybersecurity assistant.\n"
        "Generate a clear description of the following Linux command.\n\n"
        f"Command: {command}\n"
        f"Current Working Directory: {cwd}\n"
        f"Intent: {intent}\n\n"
        "Description:"
    )


    inputs = _desc_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(device)


    with torch.no_grad():
        output_ids = _desc_model.generate(
            **inputs,
            max_length=90,
            num_beams=5,
            early_stopping=True,
        )


    description = _desc_tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True,
    ).strip()


    return description or "Description not available."




# ============================================================
# SESSION SUMMARY
# ============================================================


def generate_session_summary(commands: List[Dict[str, Any]]) -> str:
    """
    Uses Cerebras if available. Falls back to local rule-based summary.
    """


    if not commands:
        return "No commands were recorded in this session."


    text = "\n".join(
        [
            f"{cmd.get('command', '')} -> {cmd.get('intent', '')}: {cmd.get('description', '')}"
            for cmd in commands
        ]
    )


    if _cerebras_client is not None:
        try:
            prompt = f"""
Summarize this SSH honeypot terminal session in proper sentences and explain the session properly.
Focus on attacker behavior, likely goal, and any suspicious activity.



Session:
{text}
"""


            completion = _cerebras_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3.1-8b",
                max_completion_tokens=150,
                temperature=0.3,
            )


            return completion.choices[0].message.content.strip()


        except Exception as e:
            print(f"[BehaviorEngine] Cerebras summary failed: {e}")


    # Local fallback summary
    commands_text = [cmd.get("command", "") for cmd in commands]
    intents = [cmd.get("intent", "") for cmd in commands]


    unique_intents = sorted(set([i for i in intents if i]))


    if unique_intents:
        intent_text = ", ".join(unique_intents[:5])
    else:
        intent_text = "unknown activity"


    first_cmd = commands_text[0] if commands_text else "unknown"
    last_cmd = commands_text[-1] if commands_text else "unknown"


    return (
        f"The session contains {len(commands)} recorded commands, beginning with '{first_cmd}' "
        f"and ending with '{last_cmd}'. The observed behavior appears related to {intent_text}."
    )




# ============================================================
# MAIN PROCESSOR
# ============================================================


def analyze_sessions(
    input_file: Optional[Path] = None,
    output_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Reads logs/sessions_clean.json and writes data/session_commands_with_intent.json.
    """


    load_behavior_models()


    input_file = input_file or INPUT_FILE
    output_file = output_file or OUTPUT_FILE


    DATA_DIR.mkdir(parents=True, exist_ok=True)


    if not input_file.exists():
        raise FileNotFoundError(f"Input session file not found: {input_file}")


    with open(input_file, "r", encoding="utf-8") as f:
        sessions = json.load(f)


    if not isinstance(sessions, list):
        raise ValueError("sessions_clean.json must contain a list of sessions.")


    results = []


    for session in sessions:
        session_id = session.get("session_id", "unknown")
        session_commands = session.get("commands", [])


        session_result = {
            "session_id": session_id,
            "remote_addr": session.get("remote_addr", "unknown"),
            "username": session.get("username", "unknown"),
            "started_at": session.get("started_at", ""),
            "ended_at": session.get("ended_at", ""),
            "command_count": len(session_commands),
            "commands": [],
            "summary": "",
        }


        for cmd_obj in session_commands:
            command = cmd_obj.get("command", "")
            cwd = cmd_obj.get("cwd", "/")
            output = cmd_obj.get("output", "")
            command_index = cmd_obj.get("command_index")


            intent = predict_intent(command)
            description = generate_description(command, intent, cwd)


            session_result["commands"].append(
                {
                    "command_index": command_index,
                    "command": command,
                    "cwd": cwd,
                    "output": output,
                    "intent": intent,
                    "description": description,
                }
            )


        session_result["summary"] = generate_session_summary(
            session_result["commands"]
        )


        results.append(session_result)


    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)


    print(f"[BehaviorEngine] Processing complete. Saved to {output_file}")


    return {
        "status": "completed",
        "sessions_processed": len(results),
        "output_file": str(output_file),
    }




def load_analysis_results(output_file: Optional[Path] = None):
    output_file = output_file or OUTPUT_FILE


    if not output_file.exists():
        return []


    with open(output_file, "r", encoding="utf-8") as f:
        return json.load(f)




if __name__ == "__main__":
    analyze_sessions()
