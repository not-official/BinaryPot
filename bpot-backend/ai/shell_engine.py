from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

try:
    from transformers import BitsAndBytesConfig
    BNB_AVAILABLE = True
except Exception:
    BitsAndBytesConfig = None
    BNB_AVAILABLE = False

from peft import PeftModel


class ShellEngine:
    def __init__(
        self,
        adapter_dir: str = "models/binarypot-qwen25-7b-qlora",
        base_model_name: str = "Qwen/Qwen2.5-7B-Instruct",
    ) -> None:
        self.adapter_dir = Path(adapter_dir)
        self.base_model_name = base_model_name

        self.device = self._detect_device()
        self.tokenizer = None
        self.model = None

    def _detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        print(f"[ShellEngine] Loading tokenizer from {self.base_model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print(f"[ShellEngine] Loading base model on {self.device}...")

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
            dtype = torch.float32
            if self.device == "cuda":
                dtype = torch.float16

            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                torch_dtype=dtype,
                trust_remote_code=True,
            )

            if self.device == "cuda":
                base_model = base_model.to("cuda")

        print(f"[ShellEngine] Attaching adapter from {self.adapter_dir}...")
        self.model = PeftModel.from_pretrained(base_model, str(self.adapter_dir))
        self.model.eval()

        if self.device == "cpu":
            self.model = self.model.to("cpu")

        print("[ShellEngine] Model ready.")

    def build_prompt(
        self,
        command: str,
        state: Dict[str, Any],
    ) -> str:
        hostname = state.get("hostname", "web01")
        os_name = state.get("os", "Ubuntu 20.04")
        user = state.get("user", "www-data")
        cwd = state.get("cwd", "/home/ubuntu")
        installed_tools = state.get("installed_tools", "")
        extra_rules = state.get("extra_rules", "")

        state_lines = [
            f"hostname={hostname}",
            f"os={os_name}",
            f"user={user}",
            f"cwd={cwd}",
        ]

        if installed_tools:
            if isinstance(installed_tools, (list, tuple)):
                installed_tools = ",".join(installed_tools)
            state_lines.append(f"installed_tools={installed_tools}")

        if extra_rules:
            state_lines.append(str(extra_rules).strip())

        state_block = "\n".join(state_lines)

        prompt = (
            "System: You are a Linux shell inside a honeypot. "
            "Respond ONLY with realistic terminal output. "
            "Do not explain anything. Never break character.\n\n"
            f"User:\n[STATE]\n{state_block}\n\n[CMD]\n{command}\n\nAssistant:"
        )
        return prompt

    def generate_shell_response(
        self,
        command: str,
        state: Dict[str, Any],
        max_new_tokens: int = 160,
    ) -> str:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("BinaryPot model not loaded. Call load() first.")

        prompt = self.build_prompt(command, state)
        inputs = self.tokenizer(prompt, return_tensors="pt")

        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        if "Assistant:" in full_text:
            response = full_text.split("Assistant:", 1)[1].strip()
        else:
            response = full_text.strip()

        return response