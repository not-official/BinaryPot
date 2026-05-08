"""
Optimized FakeShell for BinaryPot.

Features:
- Fast hardcoded Linux-like commands
- Persistent fake filesystem using file_structure.txt
- Local Qwen ShellEngine fallback
- AI response cache for repeated commands
- Faster handling for random unknown commands
- Hybrid wget/git clone support
"""

from pathlib import Path
from typing import Dict, Any
import asyncio
import json
import shlex
import time
from datetime import datetime
import uuid

from .logger import log_command
from ai.shell_engine import ShellEngine


STRUCT_FILE = Path(__file__).parent / "file_structure.txt"

DEFAULT_STRUCTURE = {
    "/": ["home", "etc", "var", "tmp"],
    "/home": ["asus"],
    "/home/asus": ["notes.txt", "secrets.txt"],
    "/home/asus/notes.txt": "These are sample notes.\nTry 'cat notes.txt'\n",
    "/home/asus/secrets.txt": "This file is an illusion.\n",
    "/etc": ["issue", "passwd", "hostname"],
    "/etc/issue": "Ubuntu 20.04.6 LTS\n",
    "/etc/hostname": "web01\n",
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        "ubuntu:x:1000:1000:Ubuntu:/home/ubuntu:/bin/bash\n"
    ),
}

AI_CACHE = {}
MAX_CACHE_SIZE = 300

AI_ALLOWED_COMMANDS = {
    "curl", "wget", "git", "python", "python3", "pip", "pip3",
    "apt", "apt-get", "sudo", "find", "grep", "tar", "nc",
    "netcat", "ssh", "scp", "chmod", "chown", "bash", "sh",
    "uname", "id", "ps", "cat",
}

LOCAL_SHELL_ENGINE = ShellEngine(
    adapter_dir="models/binarypot-qwen25-1.5b-qlora",
    base_model_name="Qwen/Qwen2.5-1.5B-Instruct",
)

_ENGINE_LOADED = False


def load_local_shell_engine_once():
    global _ENGINE_LOADED
    if not _ENGINE_LOADED:
        LOCAL_SHELL_ENGINE.load()
        _ENGINE_LOADED = True


load_local_shell_engine_once()


# ============================================================
# FILESYSTEM HELPERS
# ============================================================

def normalize_structure(raw):
    dirs, files, mtimes = {}, {}, {}

    if isinstance(raw, dict) and ("dirs" in raw or "files" in raw):
        return {
            "dirs": {k: list(v) for k, v in raw.get("dirs", {}).items()},
            "files": {k: str(v) for k, v in raw.get("files", {}).items()},
            "mtimes": raw.get("mtimes", {}),
        }

    for path, value in raw.items():
        clean = path.rstrip("/") if path != "/" else "/"
        if isinstance(value, list):
            dirs[clean] = list(value)
        else:
            files[path] = str(value)
            mtimes[path] = int(time.time())

    dirs.setdefault("/", [])
    return {"dirs": dirs, "files": files, "mtimes": mtimes}


def load_structure():
    if not STRUCT_FILE.exists():
        save_structure(normalize_structure(DEFAULT_STRUCTURE))
        return normalize_structure(DEFAULT_STRUCTURE)

    try:
        return normalize_structure(json.loads(STRUCT_FILE.read_text(encoding="utf-8")))
    except Exception:
        struct = normalize_structure(DEFAULT_STRUCTURE)
        save_structure(struct)
        return struct


def save_structure(struct):
    tmp = STRUCT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(struct, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STRUCT_FILE)


def now():
    return int(time.time())


def fmt_time(epoch):
    return datetime.fromtimestamp(epoch).strftime("%m/%d/%Y %I:%M %p")


def size_of(content):
    return len(str(content).encode("utf-8"))


# ============================================================
# FAKE SHELL
# ============================================================

class FakeShell:
    def __init__(self, chan, addr: str, username: str, session_id: str = None):
        self.chan = chan
        self.addr = addr
        self.username = username
        self.session_id = session_id or str(uuid.uuid4())[:8]

        self.hostname = "web01"
        self.os_name = "Ubuntu 20.04"
        self.env_home = f"/home/{username}"
        self.cwd = self.env_home

        self.struct = load_structure()
        self.struct.setdefault("dirs", {})
        self.struct.setdefault("files", {})
        self.struct.setdefault("mtimes", {})

        self.command_history = []
        self.command_index = 0

        self._mkdir_virtual("/home")
        self._mkdir_virtual(self.env_home)
        save_structure(self.struct)

    # ========================================================
    # BASIC HELPERS
    # ========================================================

    def write(self, output=""):
        self.chan.write((output or "") + "\r\n")

    def _log(self, cmd: str, output: str = ""):
        try:
            log_command(
                self.addr,
                self.username,
                cmd,
                session_id=self.session_id,
                output=output,
                cwd=self.cwd,
                command_index=self.command_index,
            )
        except TypeError:
            log_command(
                self.addr,
                self.username,
                cmd,
                session_id=self.session_id,
                output=output,
            )
        except Exception as e:
            print(f"Logging error: {e}")

    def _normpath(self, path: str) -> str:
        if not path:
            return self.cwd

        path = path.strip()

        if path.startswith("~"):
            path = path.replace("~", self.env_home, 1)

        if not path.startswith("/"):
            path = self.cwd.rstrip("/") + "/" + path

        parts = []

        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return "/" + "/".join(parts) if parts else "/"

    def _parent_name(self, path: str):
        clean = path.rstrip("/")
        parent = "/" + "/".join(clean.strip("/").split("/")[:-1])
        name = clean.split("/")[-1]
        return parent if parent != "" else "/", name

    def _is_dir(self, path: str):
        path = path.rstrip("/") if path != "/" else "/"
        return path in self.struct["dirs"]

    def _is_file(self, path: str):
        return path in self.struct["files"]

    def _mkdir_virtual(self, path: str):
        path = self._normpath(path)

        if self._is_dir(path):
            return

        parent, name = self._parent_name(path)

        if not self._is_dir(parent):
            self._mkdir_virtual(parent)

        self.struct["dirs"][path] = []
        self.struct.setdefault("mtimes", {})[path] = now()

        if name and name not in self.struct["dirs"].get(parent, []):
            self.struct["dirs"].setdefault(parent, []).append(name)

    def _add_file(self, path: str, content: str = ""):
        path = self._normpath(path)
        parent, name = self._parent_name(path)

        if not self._is_dir(parent):
            self._mkdir_virtual(parent)

        self.struct["files"][path] = content
        self.struct.setdefault("mtimes", {})[path] = now()

        if name not in self.struct["dirs"].get(parent, []):
            self.struct["dirs"].setdefault(parent, []).append(name)

        save_structure(self.struct)

    def _remove_file(self, path: str):
        path = self._normpath(path)
        parent, name = self._parent_name(path)

        self.struct["files"].pop(path, None)
        self.struct.get("mtimes", {}).pop(path, None)

        if name in self.struct["dirs"].get(parent, []):
            self.struct["dirs"][parent].remove(name)

        save_structure(self.struct)

    def _remove_dir(self, path: str):
        path = self._normpath(path)

        if not self._is_dir(path) or self.struct["dirs"].get(path):
            return False

        parent, name = self._parent_name(path)

        self.struct["dirs"].pop(path, None)
        self.struct.get("mtimes", {}).pop(path, None)

        if name in self.struct["dirs"].get(parent, []):
            self.struct["dirs"][parent].remove(name)

        save_structure(self.struct)
        return True

    # ========================================================
    # LOCAL MODEL
    # ========================================================

    def _model_state(self) -> Dict[str, Any]:
        return {
            "hostname": self.hostname,
            "os": self.os_name,
            "user": self.username,
            "cwd": self.cwd,
            "installed_tools": ["git", "curl", "wget", "python3"],
            "extra_rules": (
                "IMPORTANT ENVIRONMENT RULES:\n"
                "- git, curl, wget, and python3 are installed and available in PATH.\n"
                "- GitHub is reachable.\n"
                "- DNS resolution works.\n"
                "- Output terminal text only.\n"
                "- Do not explain anything.\n"
                "- Do not include markdown.\n"
                "- Do not say you are an AI.\n"
                "- Do not include the shell prompt.\n"
            ),
        }

    def _cache_key(self, cmdline: str, max_new_tokens: int):
        state = self._model_state()
        return (
            cmdline,
            state["user"],
            state["cwd"],
            tuple(state["installed_tools"]),
            max_new_tokens,
        )

    async def _ai(self, cmdline: str, max_new_tokens: int = 60):
        key = self._cache_key(cmdline, max_new_tokens)

        if key in AI_CACHE:
            return AI_CACHE[key]

        output = await asyncio.to_thread(
            LOCAL_SHELL_ENGINE.generate_shell_response,
            cmdline,
            self._model_state(),
            max_new_tokens,
        )

        output = (output or "").strip()

        if len(AI_CACHE) >= MAX_CACHE_SIZE:
            AI_CACHE.pop(next(iter(AI_CACHE)))

        AI_CACHE[key] = output
        return output

    def _should_use_ai(self, cmd: str, cmdline: str):
        if cmd in AI_ALLOWED_COMMANDS:
            return True

        if any(x in cmdline for x in ["|", "&&", ";", "$(", "`", ">", "<"]):
            return True

        return False

    async def _fake_file_content(self, path: str):
        prompt = (
            f"cat {path}\n"
            "Generate realistic Linux file content only. "
            "No explanation. No markdown."
        )

        output = await self._ai(prompt, max_new_tokens=100)

        bad = ["no such file", "command not found", "cannot access", "not found"]

        if not output or any(x in output.lower() for x in bad):
            return ""

        return output

    async def _hybrid_download(self, cmdline: str, filename: str, is_dir=False):
        target = self._normpath(filename)

        if is_dir:
            self._mkdir_virtual(target)
            save_structure(self.struct)
        else:
            self._add_file(
                target,
                f"Downloaded content for {filename}\nGenerated by command: {cmdline}\n",
            )

        return await self._ai(cmdline, max_new_tokens=120)

    # ========================================================
    # COMMAND HANDLER
    # ========================================================

    async def handle(self, cmdline: str):
        if not cmdline or not cmdline.strip():
            self.write()
            return

        cmdline = cmdline.strip()
        output = ""

        try:
            parts = shlex.split(cmdline)
        except ValueError as e:
            output = f"bash: syntax error: {e}"
            self.write(output)
            self._log(cmdline, output)
            return

        if not parts:
            self.write()
            return

        cmd, args = parts[0], parts[1:]

        self.command_index += 1
        self.command_history.append(cmdline)
        self.command_history = self.command_history[-10:]

        try:
            # ---------------- EXIT ----------------
            if cmd in ("exit", "logout"):
                output = "logout"
                self.write(output)
                self._log(cmdline, output)
                raise EOFError("exit requested")

            # ---------------- SIMPLE COMMANDS ----------------
            if cmd == "whoami":
                output = self.username

            elif cmd == "pwd":
                output = self.cwd

            elif cmd == "echo":
                output = " ".join(args)

            elif cmd == "clear":
                self.chan.write("\x1b[2J\x1b[H")
                self._log(cmdline, "SUCCESS: screen cleared")
                return

            elif cmd == "uname":
                output = (
                    "Linux web01 5.15.0-89-generic #99-Ubuntu SMP "
                    "Mon Oct 30 20:42:41 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
                    if args and args[0] == "-a"
                    else "Linux"
                )

            elif cmd == "id":
                output = (
                    f"uid=1000({self.username}) "
                    f"gid=1000({self.username}) "
                    f"groups=1000({self.username})"
                )

            elif cmd == "ps":
                output = "\n".join([
                    "  PID TTY          TIME CMD",
                    "    1 ?        00:00:01 systemd",
                    "  123 ?        00:00:00 sshd",
                    "  456 pts/0    00:00:00 bash",
                ])

            elif cmd == "help":
                output = "\n".join([
                    "Available commands:",
                    "  ls, cd, pwd, cat, echo, touch, rm, mkdir, rmdir",
                    "  whoami, id, uname, ps, clear, help, exit",
                    "  wget, curl, git clone",
                ])

            # ---------------- CD ----------------
            elif cmd == "cd":
                target = args[0] if args else "~"
                path = self._normpath(target)

                if self._is_dir(path):
                    self.cwd = path
                else:
                    output = f"cd: {target}: No such file or directory"

            # ---------------- LS ----------------
            elif cmd == "ls":
                target = args[-1] if args and not args[-1].startswith("-") else "."
                path = self._normpath(target)

                if self._is_file(path):
                    output = path.rstrip("/").split("/")[-1]

                elif not self._is_dir(path):
                    output = f"ls: cannot access '{target}': No such file or directory"

                else:
                    entries = sorted(self.struct["dirs"].get(path, []))

                    if "-la" in args or "-l" in args:
                        lines = []

                        for entry in entries:
                            full = path.rstrip("/") + "/" + entry if path != "/" else "/" + entry
                            is_dir = self._is_dir(full)
                            mode = "drwxr-xr-x" if is_dir else "-rw-r--r--"
                            size = 4096 if is_dir else size_of(self.struct["files"].get(full, ""))
                            mtime = fmt_time(self.struct.get("mtimes", {}).get(full, now()))
                            lines.append(f"{mode} 1 {self.username} {self.username} {size:>6} {mtime} {entry}")

                        output = "\n".join(lines)
                    else:
                        output = "  ".join(entries)

            # ---------------- MKDIR ----------------
            elif cmd == "mkdir":
                if not args:
                    output = "mkdir: missing operand"
                else:
                    errors = []

                    for name in args:
                        path = self._normpath(name)

                        if self._is_dir(path) or self._is_file(path):
                            errors.append(f"mkdir: cannot create directory '{name}': File exists")
                        else:
                            self._mkdir_virtual(path)

                    save_structure(self.struct)
                    output = "\n".join(errors)

            # ---------------- RMDIR ----------------
            elif cmd == "rmdir":
                if not args:
                    output = "rmdir: missing operand"
                else:
                    errors = []

                    for name in args:
                        path = self._normpath(name)

                        if not self._is_dir(path):
                            errors.append(f"rmdir: failed to remove '{name}': No such directory")
                        elif self.struct["dirs"].get(path):
                            errors.append(f"rmdir: failed to remove '{name}': Directory not empty")
                        else:
                            self._remove_dir(path)

                    output = "\n".join(errors)

            # ---------------- TOUCH ----------------
            elif cmd == "touch":
                if not args:
                    output = "touch: missing file operand"
                else:
                    errors = []

                    for name in args:
                        path = self._normpath(name)

                        if self._is_dir(path):
                            errors.append(f"touch: cannot touch '{name}': Is a directory")
                        else:
                            if not self._is_file(path):
                                self._add_file(path, "")
                            else:
                                self.struct["mtimes"][path] = now()
                                save_structure(self.struct)

                    output = "\n".join(errors)

            # ---------------- RM ----------------
            elif cmd == "rm":
                if not args:
                    output = "rm: missing operand"
                else:
                    errors = []

                    for name in args:
                        path = self._normpath(name)

                        if self._is_file(path):
                            self._remove_file(path)
                        elif self._is_dir(path):
                            errors.append(f"rm: cannot remove '{name}': Is a directory")
                        else:
                            errors.append(f"rm: cannot remove '{name}': No such file or directory")

                    output = "\n".join(errors)

            # ---------------- CAT ----------------
            elif cmd == "cat":
                if not args:
                    output = "cat: missing file operand"
                else:
                    results = []

                    for name in args:
                        path = self._normpath(name)

                        if self._is_dir(path):
                            results.append(f"cat: {name}: Is a directory")

                        elif self._is_file(path):
                            results.append(self.struct["files"].get(path, "").rstrip())

                        else:
                            generated = await self._fake_file_content(path)

                            if generated:
                                self._add_file(path, generated)
                                results.append(generated.rstrip())
                            else:
                                results.append(f"cat: {name}: No such file or directory")

                    output = "\n".join(results)

            # ---------------- CURL HEAD FAST PATH ----------------
            elif cmd == "curl" and "-I" in args:
                url = args[-1]
                output = "\n".join([
                    "HTTP/1.1 200 OK",
                    "Content-Type: text/html; charset=UTF-8",
                    "Connection: keep-alive",
                    "Server: ECS",
                    f"X-Request-URL: {url}",
                ])

            # ---------------- WGET HYBRID ----------------
            elif cmd == "wget":
                if not args:
                    output = "wget: missing URL"
                else:
                    url = args[-1]
                    filename = url.split("/")[-1] or "index.html"

                    output = await self._hybrid_download(
                        cmdline,
                        filename,
                        is_dir=False,
                    )

                    if not output:
                        output = (
                            f"--{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n"
                            f"Resolving {url.split('/')[2] if '://' in url else url}... connected.\n"
                            "HTTP request sent, awaiting response... 200 OK\n"
                            f"Saving to: '{filename}'\n\n"
                            f"'{filename}' saved"
                        )

            # ---------------- GIT CLONE HYBRID ----------------
            elif cmd == "git" and args and args[0] == "clone":
                if len(args) < 2:
                    output = "fatal: repository argument required"
                else:
                    repo_url = args[1]
                    folder = repo_url.rstrip("/").split("/")[-1].replace(".git", "") or "repo"
                    target_path = self._normpath(folder)

                    if self._is_dir(target_path) or self._is_file(target_path):
                        output = f"fatal: destination path '{folder}' already exists and is not an empty directory."
                    else:
                        # Create cloned repo folder
                        self._mkdir_virtual(target_path)

                        # Add normal repo files
                        self._add_file(
                            f"{target_path}/README.md",
                            f"# {folder}\n\nThis is a cloned repository.\n"
                        )

                        self._add_file(
                            f"{target_path}/.gitignore",
                            "__pycache__/\n.env\n*.log\n"
                        )

                        self._add_file(
                            f"{target_path}/main.py",
                            "print('Hello from cloned repository')\n"
                        )

                        self._add_file(
                            f"{target_path}/requirements.txt",
                            "requests==2.31.0\nflask==2.3.2\n"
                        )

                        # Add fake .git structure
                        self._mkdir_virtual(f"{target_path}/.git")
                        self._mkdir_virtual(f"{target_path}/.git/objects")
                        self._mkdir_virtual(f"{target_path}/.git/refs")
                        self._mkdir_virtual(f"{target_path}/.git/refs/heads")

                        self._add_file(
                            f"{target_path}/.git/HEAD",
                            "ref: refs/heads/main\n"
                        )

                        self._add_file(
                            f"{target_path}/.git/config",
                            (
                                "[core]\n"
                                "\trepositoryformatversion = 0\n"
                                "\tfilemode = true\n"
                                "\tbare = false\n"
                                "\tlogallrefupdates = true\n"
                                "[remote \"origin\"]\n"
                                f"\turl = {repo_url}\n"
                                "\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
                                "[branch \"main\"]\n"
                                "\tremote = origin\n"
                                "\tmerge = refs/heads/main\n"
                            )
                        )

                        save_structure(self.struct)

                        output = "\n".join([
                            f"Cloning into '{folder}'...",
                            "remote: Enumerating objects: 48, done.",
                            "remote: Counting objects: 100% (48/48), done.",
                            "remote: Compressing objects: 100% (32/32), done.",
                            "remote: Total 48 (delta 12), reused 41 (delta 8), pack-reused 0",
                            "Receiving objects: 100% (48/48), 12.43 KiB | 1.24 MiB/s, done.",
                            "Resolving deltas: 100% (12/12), done.",
                        ])

            # ---------------- AI TEST ----------------
            elif cmd == "ai_test":
                prompt = cmdline[len("ai_test"):].strip()
                output = await self._ai(prompt, max_new_tokens=80)

            # ---------------- UNKNOWN ----------------
            else:
                if self._should_use_ai(cmd, cmdline):
                    output = await self._ai(cmdline, max_new_tokens=60)

                if not output:
                    output = f"{cmd}: command not found"

        finally:
            if output:
                self.write(output)
            else:
                self.write()

            self._log(cmdline, output[:1000] if output else "")

    def prompt(self):
        return f"@root:{self.cwd}$ "