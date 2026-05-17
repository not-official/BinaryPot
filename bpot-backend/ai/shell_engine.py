# honeypot/shell_engine.py

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
        print("=" * 60)
        print("[ShellEngine] Starting model loader...")

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[ShellEngine] NVIDIA GPU detected: {gpu_name}")
            print("[ShellEngine] Using CUDA GPU mode.")
        else:
            print("[ShellEngine] No CUDA GPU detected.")
            print("[ShellEngine] Using CPU mode.")

        print("=" * 60)

        print("[ShellEngine] Loading tokenizer...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("[ShellEngine] Loading base model...")

        # GPU MODE
        if self.device == "cuda":
            if BNB_AVAILABLE:
                print("[ShellEngine] bitsandbytes available.")
                print("[ShellEngine] Loading model in 4-bit GPU mode...")

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
                print("[ShellEngine] bitsandbytes not available.")
                print("[ShellEngine] Loading model in normal FP16 GPU mode...")

                base_model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True,
                )

        # CPU MODE
        else:
            print("[ShellEngine] Loading model in CPU mode...")
            print("[ShellEngine] This may be slow on non-GPU systems.")

            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                torch_dtype=torch.float32,
                trust_remote_code=True,
            )

            base_model.to("cpu")

        print("[ShellEngine] Loading LoRA adapter...")

        if not self.adapter_dir.exists():
            raise FileNotFoundError(
                f"LoRA adapter folder not found: {self.adapter_dir}"
            )

        self.model = PeftModel.from_pretrained(
            base_model,
            str(self.adapter_dir),
        )

        self.model.eval()

        print("[ShellEngine] Model loaded successfully.")
        print("[ShellEngine] Ready.")
        print("=" * 60)

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

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
        )

        # Move input tensors to GPU only if CUDA is available
        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        else:
            inputs = {k: v.to("cpu") for k, v in inputs.items()}

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

        full_text = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
        )

        if "Assistant:" in full_text:
            response = full_text.split("Assistant:", 1)[1].strip()
        else:
            response = full_text.strip()

        return self.clean_response(response)

    def clean_response(self, response: str) -> str:
        """
        Cleans unwanted model artifacts so the honeypot shell looks more realistic.
        """

        unwanted_prefixes = [
            "Assistant:",
            "System:",
            "User:",
            "[CMD]",
            "[STATE]",
        ]

        for prefix in unwanted_prefixes:
            if response.startswith(prefix):
                response = response.replace(prefix, "", 1).strip()

        return response.strip()
