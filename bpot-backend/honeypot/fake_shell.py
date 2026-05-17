# fake_shell.py
"""
BinaryPot FakeShell


Refined version:
- Shared fake filesystem using honeypot_fs
- No per-attacker/per-username folder creation
- Everyone starts in /home/user
- Only core filesystem/navigation commands are hardcoded
- All other commands go to AI fallback
- wget and git clone still modify honeypot_fs
- cat can ask AI to generate realistic fake file content
- AI model loads when honeypot starts
- No tab functionality
"""


import asyncio
import os
import shlex
import shutil
import uuid
from datetime import datetime
from pathlib import Path


from .logger import log_command




# ============================================================
# OPTIONAL AI FALLBACK
# ============================================================


try:
    from ai.shell_engine import ShellEngine
except Exception as e:
    print(f"[FakeShell] ShellEngine import failed: {e}")
    ShellEngine = None




LOCAL_SHELL_ENGINE = None
_ENGINE_LOADED = False


AI_CACHE = {}
MAX_CACHE_SIZE = 300




def load_local_shell_engine_once():
    global LOCAL_SHELL_ENGINE, _ENGINE_LOADED


    if ShellEngine is None:
        print("[FakeShell] AI disabled because ShellEngine is unavailable.")
        return None


    if _ENGINE_LOADED:
        return LOCAL_SHELL_ENGINE


    try:
        print("[FakeShell] Loading local ShellEngine...")


        LOCAL_SHELL_ENGINE = ShellEngine(
            adapter_dir="models/binarypot-qwen25-1.5b-qlora",
            base_model_name="Qwen/Qwen2.5-1.5B-Instruct",
        )


        if hasattr(LOCAL_SHELL_ENGINE, "load"):
            LOCAL_SHELL_ENGINE.load()


        _ENGINE_LOADED = True
        print("[FakeShell] Local ShellEngine loaded successfully.")
        return LOCAL_SHELL_ENGINE


    except Exception as e:
        print(f"[FakeShell] AI engine load failed: {e}")
        LOCAL_SHELL_ENGINE = None
        _ENGINE_LOADED = True
        return None




# Load model immediately when run_honeypot imports FakeShell
load_local_shell_engine_once()




# ============================================================
# FAKE FILESYSTEM
# ============================================================


BASE_FS = Path(__file__).parent.parent / "honeypot_fs"
BASE_FS.mkdir(parents=True, exist_ok=True)


DEFAULT_USER = "user"
DEFAULT_HOSTNAME = "web01"
DEFAULT_HOME = "/home/user"




DEFAULT_DIRS = [
    "/",
    "/home",
    "/home/user",
    "/home/user/Downloads",
    "/home/user/Documents",
    "/etc",
    "/var",
    "/var/log",
    "/tmp",
    "/root",
]




DEFAULT_FILES = {
    "/etc/issue": "Ubuntu 20.04.6 LTS \\n \\l\n",


    "/etc/hostname": "web01\n",


    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        "user:x:1000:1000:User:/home/user:/bin/bash\n"
    ),


    "/etc/group": (
        "root:x:0:\n"
        "sudo:x:27:user\n"
        "www-data:x:33:\n"
        "user:x:1000:\n"
    ),


    "/etc/os-release": (
        'NAME="Ubuntu"\n'
        'VERSION="20.04.6 LTS (Focal Fossa)"\n'
        'ID=ubuntu\n'
        'PRETTY_NAME="Ubuntu 20.04.6 LTS"\n'
        'VERSION_ID="20.04"\n'
    ),


    "/home/user/notes.txt": (
        "TODO:\n"
        "- Check logs\n"
        "- Review SSH access\n"
        "- Update scripts\n"
    ),


    "/home/user/secrets.txt": (
        "This is a decoy file.\n"
        "No real secrets are stored here.\n"
    ),


    "/home/user/.bash_history": (
        "ls -la\n"
        "cat /etc/passwd\n"
        "cd /var/log\n"
        "cat auth.log\n"
    ),


    "/var/log/auth.log": (
        "May 16 10:21:14 web01 sshd[1122]: Server listening on 0.0.0.0 port 22.\n"
        "May 16 10:23:02 web01 sshd[1240]: Accepted password for user from 192.168.1.15 port 49822 ssh2\n"
    ),
}




# ============================================================
# HELPERS
# ============================================================


def fmt_time(epoch):
    return datetime.fromtimestamp(epoch).strftime("%b %d %H:%M")




def file_size(path: Path):
    try:
        if path.is_file():
            return path.stat().st_size
        return 4096
    except Exception:
        return 0




def clean_ai_output(output: str):
    if not output:
        return ""


    output = str(output).strip()


    bad_prefixes = [
        "Here is",
        "Sure",
        "The command",
        "This command",
        "As an AI",
        "I cannot",
        "I can't",
        "```bash",
        "```",
    ]


    cleaned = []


    for line in output.splitlines():
        stripped = line.strip()


        if any(stripped.startswith(prefix) for prefix in bad_prefixes):
            continue


        if stripped.startswith("$ "):
            stripped = stripped[2:]


        if stripped.startswith("# "):
            stripped = stripped[2:]


        cleaned.append(stripped)


    final = "\n".join(cleaned).strip()
    final = final.replace("```bash", "").replace("```", "").strip()


    return final




# ============================================================
# FAKE SHELL
# ============================================================


class FakeShell:
    def __init__(self, chan, addr: str, username: str, session_id: str = None):
        self.chan = chan
        self.addr = addr


        # Real login username is logged only.
        # Fake Linux username remains consistent for every attacker.
        self.login_username = username or "unknown"
        self.shell_user = DEFAULT_USER


        self.session_id = session_id or str(uuid.uuid4())[:8]


        self.hostname = DEFAULT_HOSTNAME
        self.cwd = DEFAULT_HOME
        self.env_home = DEFAULT_HOME
        self.session_root = BASE_FS


        self.command_history = []
        self.command_index = 0


        # Prevent overlapping AI command execution
        self._command_lock = asyncio.Lock()


        self._init_filesystem()


    # ========================================================
    # FILESYSTEM SETUP
    # ========================================================


    def _init_filesystem(self):
        for directory in DEFAULT_DIRS:
            real_dir = self._to_real_path(directory)
            real_dir.mkdir(parents=True, exist_ok=True)


        for vpath, content in DEFAULT_FILES.items():
            real_file = self._to_real_path(vpath)
            real_file.parent.mkdir(parents=True, exist_ok=True)


            if not real_file.exists():
                real_file.write_text(content, encoding="utf-8")


    # ========================================================
    # BASIC HELPERS
    # ========================================================


    def write(self, output=""):
        self.chan.write((output or "") + "\r\n")


    def prompt(self):
        return f"{self.shell_user}@{self.hostname}:{self.cwd}$ "


    def _log(self, cmd: str, output: str = ""):
        try:
            log_command(
                self.addr,
                self.login_username,
                cmd,
                session_id=self.session_id,
                output=output,
                cwd=self.cwd,
                command_index=self.command_index,
            )
        except TypeError:
            log_command(
                self.addr,
                self.login_username,
                cmd,
                session_id=self.session_id,
                output=output,
            )
        except Exception as e:
            print(f"[FakeShell] Logging error: {e}")


    def _normpath(self, path: str) -> str:
        if not path:
            return self.cwd


        path = path.strip()


        if path == "~":
            path = self.env_home
        elif path.startswith("~/"):
            path = self.env_home + path[1:]


        if not path.startswith("/"):
            path = self.cwd.rstrip("/") + "/" + path


        parts = []


        for part in path.split("/"):
            if part in ("", "."):
                continue


            if part == "..":
                if parts:
                    parts.pop()
                continue


            parts.append(part)


        return "/" + "/".join(parts) if parts else "/"


    def _to_real_path(self, vpath: str) -> Path:
        normalized = self._normpath(vpath)
        real_path = self.session_root / normalized.strip("/")


        try:
            base = self.session_root.resolve()
            target = real_path.resolve(strict=False)


            if not str(target).startswith(str(base)):
                return base
        except Exception:
            pass


        return real_path


    def _current_dir_entries(self):
        try:
            real_cwd = self._to_real_path(self.cwd)
            if not real_cwd.exists() or not real_cwd.is_dir():
                return []


            return sorted([p.name + ("/" if p.is_dir() else "") for p in real_cwd.iterdir()])
        except Exception:
            return []


    # ========================================================
    # MAIN COMMAND HANDLER
    # ========================================================


    async def handle(self, cmdline: str):
        async with self._command_lock:
            await self._handle_locked(cmdline)


    async def _handle_locked(self, cmdline: str):
        if not cmdline or not cmdline.strip():
            self.write()
            return


        cmdline = cmdline.strip()


        self.command_index += 1
        self.command_history.append(cmdline)
        self.command_history = self.command_history[-50:]


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


        cmd = parts[0]
        args = parts[1:]
        output = ""


        try:
            # ------------------------------------------------
            # CORE SHELL COMMANDS ONLY
            # ------------------------------------------------


            if cmd in ("exit", "logout"):
                output = "logout"
                self.write(output)
                self._log(cmdline, output)
                raise EOFError()


            elif cmd == "pwd":
                output = self.cwd


            elif cmd == "cd":
                output = self._cmd_cd(args)


            elif cmd == "ls":
                output = self._cmd_ls(args)


            elif cmd == "cat":
                output = await self._cmd_cat(args)


            elif cmd == "echo":
                output = self._cmd_echo(args)


            elif cmd == "touch":
                output = self._cmd_touch(args)


            elif cmd == "mkdir":
                output = self._cmd_mkdir(args)


            elif cmd == "rmdir":
                output = self._cmd_rmdir(args)


            elif cmd == "rm":
                output = self._cmd_rm(args)


            elif cmd == "clear":
                self.chan.write("\x1b[2J\x1b[H")
                self._log(cmdline, "")
                return


            elif cmd == "history":
                output = self._cmd_history()


            elif cmd == "help":
                output = self._cmd_help()


            elif cmd == "whoami":
                output = self.shell_user


            elif cmd == "hostname":
                output = self.hostname


            # ------------------------------------------------
            # FRIEND FUNCTIONALITY:
            # update honeypot_fs, but AI generates response
            # ------------------------------------------------


            elif cmd == "wget":
                output = await self._hybrid_wget(args, cmdline)


            elif cmd == "git":
                output = await self._hybrid_git(args, cmdline)


            # ------------------------------------------------
            # EVERYTHING ELSE GOES TO AI
            # ------------------------------------------------


            else:
                output = await self._ai_command(cmdline)


        except EOFError:
            raise


        except Exception as e:
            output = f"{cmd}: error: {e}"


        if output:
            self.write(output)
        else:
            self.write()


        self._log(cmdline, output[:3000] if output else "")


    # ========================================================
    # CORE COMMANDS
    # ========================================================


    def _cmd_cd(self, args):
        target = args[0] if args else "~"
        real_target = self._to_real_path(target)


        if not real_target.exists():
            return f"bash: cd: {target}: No such file or directory"


        if not real_target.is_dir():
            return f"bash: cd: {target}: Not a directory"


        self.cwd = self._normpath(target)
        return ""


    def _cmd_ls(self, args):
        show_all = False
        long_format = False
        targets = []


        for arg in args:
            if arg.startswith("-"):
                if "a" in arg:
                    show_all = True
                if "l" in arg:
                    long_format = True
            else:
                targets.append(arg)


        target = targets[0] if targets else "."
        real_target = self._to_real_path(target)


        if not real_target.exists():
            return f"ls: cannot access '{target}': No such file or directory"


        if real_target.is_file():
            return real_target.name


        try:
            entries = list(real_target.iterdir())
        except Exception:
            return f"ls: cannot open directory '{target}': Permission denied"


        if not show_all:
            entries = [entry for entry in entries if not entry.name.startswith(".")]


        entries = sorted(entries, key=lambda p: p.name.lower())


        if not long_format:
            return "  ".join(entry.name for entry in entries)


        lines = []


        for entry in entries:
            is_dir = entry.is_dir()
            mode = "d" if is_dir else "-"
            perms = "rwxr-xr-x" if is_dir else "rw-r--r--"


            owner = "root"
            group = "root"


            if "/home/user" in str(entry).replace("\\", "/"):
                owner = self.shell_user
                group = self.shell_user


            size = file_size(entry)
            mtime = fmt_time(entry.stat().st_mtime)


            lines.append(
                f"{mode}{perms} 1 {owner} {group} {size:>6} {mtime} {entry.name}"
            )


        return "\n".join(lines)


    async def _cmd_cat(self, args):
        if not args:
            return "cat: missing file operand"


        results = []


        for arg in args:
            real_path = self._to_real_path(arg)


            if real_path.exists() and real_path.is_dir():
                results.append(f"cat: {arg}: Is a directory")
                continue


            if real_path.exists() and real_path.is_file():
                try:
                    results.append(real_path.read_text(encoding="utf-8", errors="ignore").rstrip())
                except Exception:
                    results.append(f"cat: {arg}: Permission denied")
                continue


            # Friend-style feature:
            # If the file does not exist, ask AI to generate realistic content.
            generated = await self._fake_file_content(arg)


            if generated:
                try:
                    real_path.parent.mkdir(parents=True, exist_ok=True)
                    real_path.write_text(generated + "\n", encoding="utf-8")
                except Exception:
                    pass


                results.append(generated.rstrip())
            else:
                results.append(f"cat: {arg}: No such file or directory")


        return "\n".join(results)


    def _cmd_echo(self, args):
        if not args:
            return ""


        if ">" in args or ">>" in args:
            append = ">>" in args
            operator = ">>" if append else ">"


            try:
                index = args.index(operator)
            except ValueError:
                return "bash: syntax error"


            text = " ".join(args[:index])
            target = args[index + 1] if index + 1 < len(args) else None


            if not target:
                return "bash: syntax error near unexpected token `newline'"


            real_path = self._to_real_path(target)
            real_path.parent.mkdir(parents=True, exist_ok=True)


            mode = "a" if append else "w"


            try:
                with open(real_path, mode, encoding="utf-8") as f:
                    f.write(text + "\n")
            except Exception:
                return f"bash: {target}: Permission denied"


            return ""


        return " ".join(args)


    def _cmd_touch(self, args):
        if not args:
            return "touch: missing file operand"


        errors = []


        for arg in args:
            real_path = self._to_real_path(arg)


            if real_path.exists() and real_path.is_dir():
                errors.append(f"touch: cannot touch '{arg}': Is a directory")
                continue


            try:
                real_path.parent.mkdir(parents=True, exist_ok=True)
                real_path.touch(exist_ok=True)
            except Exception:
                errors.append(f"touch: cannot touch '{arg}': Permission denied")


        return "\n".join(errors)


    def _cmd_mkdir(self, args):
        if not args:
            return "mkdir: missing operand"


        make_parents = False
        dirs = []


        for arg in args:
            if arg == "-p":
                make_parents = True
            elif not arg.startswith("-"):
                dirs.append(arg)


        errors = []


        for d in dirs:
            real_path = self._to_real_path(d)


            if real_path.exists():
                errors.append(f"mkdir: cannot create directory '{d}': File exists")
                continue


            try:
                real_path.mkdir(parents=make_parents, exist_ok=False)
            except FileNotFoundError:
                errors.append(f"mkdir: cannot create directory '{d}': No such file or directory")
            except Exception:
                errors.append(f"mkdir: cannot create directory '{d}': Permission denied")


        return "\n".join(errors)


    def _cmd_rmdir(self, args):
        if not args:
            return "rmdir: missing operand"


        errors = []


        for d in args:
            real_path = self._to_real_path(d)


            if not real_path.exists():
                errors.append(f"rmdir: failed to remove '{d}': No such file or directory")
                continue


            if not real_path.is_dir():
                errors.append(f"rmdir: failed to remove '{d}': Not a directory")
                continue


            try:
                real_path.rmdir()
            except OSError:
                errors.append(f"rmdir: failed to remove '{d}': Directory not empty")
            except Exception:
                errors.append(f"rmdir: failed to remove '{d}': Permission denied")


        return "\n".join(errors)


    def _cmd_rm(self, args):
        if not args:
            return "rm: missing operand"


        recursive = False
        force = False
        targets = []


        for arg in args:
            if arg.startswith("-"):
                if "r" in arg or "R" in arg:
                    recursive = True
                if "f" in arg:
                    force = True
            else:
                targets.append(arg)


        errors = []


        for target in targets:
            real_path = self._to_real_path(target)


            if not real_path.exists():
                if not force:
                    errors.append(f"rm: cannot remove '{target}': No such file or directory")
                continue


            if real_path.is_dir():
                if not recursive:
                    errors.append(f"rm: cannot remove '{target}': Is a directory")
                    continue


                try:
                    shutil.rmtree(real_path)
                except Exception:
                    errors.append(f"rm: cannot remove '{target}': Permission denied")
                continue


            try:
                real_path.unlink()
            except Exception:
                errors.append(f"rm: cannot remove '{target}': Permission denied")


        return "\n".join(errors)


    def _cmd_history(self):
        return "\n".join(
            f"{i:5d}  {cmd}"
            for i, cmd in enumerate(self.command_history, start=1)
        )


    def _cmd_help(self):
        return (
            "GNU bash, version 5.0.17(1)-release (x86_64-pc-linux-gnu)\n"
            "These shell commands are defined internally.\n\n"
            "Core commands:\n"
            "ls cd pwd cat echo touch mkdir rmdir rm clear history help exit logout whoami hostname\n\n"
            "Other Linux commands are handled by the AI shell engine."
        )


    # ========================================================
    # FRIEND-STYLE HYBRID FUNCTIONS
    # ========================================================


    async def _hybrid_wget(self, args, cmdline):
        if not args:
            return "wget: missing URL"


        url = None
        output_name = None


        i = 0
        while i < len(args):
            if args[i] in ("-O", "--output-document") and i + 1 < len(args):
                output_name = args[i + 1]
                i += 2
                continue


            if not args[i].startswith("-"):
                url = args[i]


            i += 1


        if not url:
            return "wget: missing URL"


        filename = output_name or url.rstrip("/").split("/")[-1] or "index.html"
        real_path = self._to_real_path(filename)
        real_path.parent.mkdir(parents=True, exist_ok=True)


        try:
            real_path.write_text(
                f"Downloaded content from {url}\n",
                encoding="utf-8",
            )
        except Exception:
            return f"{filename}: Permission denied"


        ai_output = await self._ai_command(cmdline, max_new_tokens=140)


        if ai_output:
            return ai_output


        host = url.split("/")[2] if "://" in url else url.split("/")[0]


        return (
            f"--{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n"
            f"Resolving {host}... 93.184.216.34\n"
            f"Connecting to {host}|93.184.216.34|:80... connected.\n"
            "HTTP request sent, awaiting response... 200 OK\n"
            f"Saving to: '{filename}'\n\n"
            f"'{filename}' saved"
        )


    async def _hybrid_git(self, args, cmdline):
        if not args:
            return await self._ai_command(cmdline, max_new_tokens=120)


        if args[0] != "clone":
            return await self._ai_command(cmdline, max_new_tokens=120)


        if len(args) < 2:
            return "fatal: You must specify a repository to clone."


        repo_url = args[1]
        folder = repo_url.rstrip("/").split("/")[-1].replace(".git", "") or "repo"
        target = args[2] if len(args) >= 3 else folder
        real_target = self._to_real_path(target)


        if real_target.exists():
            return f"fatal: destination path '{target}' already exists and is not an empty directory."


        try:
            real_target.mkdir(parents=True, exist_ok=False)
            (real_target / ".git").mkdir(exist_ok=True)
            (real_target / ".git" / "objects").mkdir(exist_ok=True)
            (real_target / ".git" / "refs").mkdir(exist_ok=True)


            (real_target / "README.md").write_text(
                f"# {folder}\n\nFake cloned repository from {repo_url}.\n",
                encoding="utf-8",
            )


            (real_target / "main.py").write_text(
                "print('Hello from cloned repository')\n",
                encoding="utf-8",
            )


            (real_target / "requirements.txt").write_text(
                "requests==2.31.0\nflask==2.3.2\n",
                encoding="utf-8",
            )


            (real_target / ".git" / "HEAD").write_text(
                "ref: refs/heads/main\n",
                encoding="utf-8",
            )


        except Exception:
            return f"fatal: could not create work tree dir '{target}': Permission denied"


        ai_output = await self._ai_command(cmdline, max_new_tokens=160)


        if ai_output:
            return ai_output


        return (
            f"Cloning into '{target}'...\n"
            "remote: Enumerating objects: 48, done.\n"
            "remote: Counting objects: 100% (48/48), done.\n"
            "remote: Compressing objects: 100% (32/32), done.\n"
            "Receiving objects: 100% (48/48), done.\n"
            "Resolving deltas: 100% (12/12), done."
        )


    async def _fake_file_content(self, path):
        cmdline = f"cat {path}"
        output = await self._ai_command(cmdline, max_new_tokens=120)


        if not output:
            return ""


        bad = [
            "no such file",
            "cannot access",
            "not found",
            "command not found",
            "is a directory",
        ]


        lowered = output.lower()


        if any(x in lowered for x in bad):
            return ""


        return output.strip()


    # ========================================================
    # AI FALLBACK
    # ========================================================


    def _model_state(self):
        return {
            "hostname": self.hostname,
            "os": "Ubuntu 20.04.6 LTS",
            "user": self.shell_user,
            "login_username": self.login_username,
            "cwd": self.cwd,
            "home": self.env_home,
            "current_dir_entries": self._current_dir_entries(),
            "network_access": "limited",
            "filesystem_note": (
                "The shell uses a fake persistent filesystem under honeypot_fs. "
                "The visible Linux root is /. "
                "The user home is /home/user."
            ),
            "rules": (
                "Return only terminal stdout or stderr. "
                "Do not explain. "
                "Do not include markdown. "
                "Do not include a shell prompt. "
                "Do not say you are an AI. "
                "If a command is invalid, return a realistic Linux error. "
                "Keep output short and realistic."
            ),
        }


    async def _ai_command(self, cmdline: str, max_new_tokens: int = 120):
        print(f"[FakeShell] AI fallback triggered for: {cmdline}")


        key = (cmdline, self.cwd, max_new_tokens)


        if key in AI_CACHE:
            return AI_CACHE[key]


        engine = LOCAL_SHELL_ENGINE or load_local_shell_engine_once()


        if engine is None:
            return ""


        try:
            state = self._model_state()


            if hasattr(engine, "generate_shell_response"):
                output = await asyncio.to_thread(
                    engine.generate_shell_response,
                    cmdline,
                    state,
                    max_new_tokens,
                )


            elif hasattr(engine, "generate"):
                prompt = (
                    "You are a Linux shell inside an SSH honeypot.\n"
                    "Return only realistic terminal stdout or stderr.\n"
                    "No explanation. No markdown. No shell prompt.\n"
                    "If the command is invalid, return a realistic Linux error.\n"
                    f"STATE={state}\n"
                    f"[CMD] {cmdline}\n"
                )


                output = await asyncio.to_thread(engine.generate, prompt)


            elif hasattr(engine, "run"):
                output = await asyncio.to_thread(engine.run, cmdline)


            elif hasattr(engine, "infer"):
                output = await asyncio.to_thread(engine.infer, cmdline)


            else:
                return ""


            output = clean_ai_output(output)


            if len(AI_CACHE) >= MAX_CACHE_SIZE:
                AI_CACHE.pop(next(iter(AI_CACHE)))


            AI_CACHE[key] = output
            return output


        except Exception as e:
            print(f"[FakeShell] AI fallback failed: {e}")
            return ""

