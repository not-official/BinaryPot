from ai.shell_engine import ShellEngine

engine = ShellEngine(
    adapter_dir="models/binarypot-qwen25-7b-qlora",
    base_model_name="Qwen/Qwen2.5-7B-Instruct",
)

engine.load()

state = {
    "hostname": "web01",
    "os": "Ubuntu 20.04",
    "user": "www-data",
    "cwd": "/home/ubuntu",
    "installed_tools": ["git", "curl", "wget", "python3"],
    "extra_rules": (
        "This machine is inside a restricted internal network. "
        "Outbound internet access is blocked. "
        "Commands that try to access external websites should fail "
        "with realistic network errors."
    ),
}

print("TEST 1")
print(engine.generate_shell_response("whoami", state))
print("------")

print("TEST 2")
print(engine.generate_shell_response("pwd", state))
print("------")

print("TEST 3")
print(engine.generate_shell_response("curl -I http://example.com", state))
print("------")

print("TEST 4")
print(engine.generate_shell_response("git clone https://github.com/test/repo.git", state))
print("------")

print("TEST 5")
print(engine.generate_shell_response("abcxyz", state))