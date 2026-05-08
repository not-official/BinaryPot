from pathlib import Path
from typing import Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

try:
    from transformers import BitsAndBytesConfig
    BNB_AVAILABLE = True
except Exception:
    BNB_AVAILABLE = False


class ShellEngine:
    def __init__(
        self,
        adapter_dir: str = "models/binarypot-qwen25-1.5b-qlora",
        base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    ):
        self.adapter_dir = Path(adapter_dir)
        self.base_model_name = base_model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None

    def load(self):
        print(f"[ShellEngine] Device: {self.device}")
        print("[ShellEngine] Loading tokenizer...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("[ShellEngine] Loading base model...")

        if self.device == "cuda" and BNB_AVAILABLE:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )

            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                quantization_config=quant_config,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                torch_dtype=torch.float32,
                trust_remote_code=True,
            )

        print("[ShellEngine] Loading LoRA adapter...")

        self.model = PeftModel.from_pretrained(
            base_model,
            str(self.adapter_dir),
        )

        self.model.eval()
        print("[ShellEngine] Ready.")

    def build_prompt(self, command: str, state: Dict[str, Any]) -> str:
        installed_tools = state.get("installed_tools", [])

        if isinstance(installed_tools, list):
            installed_tools = ",".join(installed_tools)

        extra_rules = state.get("extra_rules", "")

        return f"""System: You are a Linux shell inside a honeypot. Respond ONLY with realistic terminal output. Do not explain anything. Never break character.

User:
[STATE]
hostname={state.get("hostname", "web01")}
os={state.get("os", "Ubuntu 20.04")}
user={state.get("user", "www-data")}
cwd={state.get("cwd", "/home/ubuntu")}
installed_tools={installed_tools}
{extra_rules}

[CMD]
{command}

Assistant:"""

    def generate_shell_response(
        self,
        command: str,
        state: Dict[str, Any],
        max_new_tokens: int = 160,
    ) -> str:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("ShellEngine not loaded. Call load() first.")

        prompt = self.build_prompt(command, state)

        inputs = self.tokenizer(prompt, return_tensors="pt")

        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                num_beams=1,
                use_cache=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        if "Assistant:" in full_text:
            return full_text.split("Assistant:", 1)[1].strip()

        return full_text.strip()