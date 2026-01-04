"""
Minimal FakeShell with PowerShell-like `ls` output.

Commands: ls, cd, whoami, mkdir, rmdir, exit, pwd, cat, echo, touch, rm, clear, uname, id, ps, help
Persists structure to file_structure.txt. Supports two structure formats:
1) Compact (your sample):
   {
     "/": ["home","etc"],
     "/home": ["asus"],
     "/home/asus/notes.txt": "content",
     ...
   }
2) Namespaced:
   {"dirs": {...}, "files": {...}}
Both are normalized internally on load.
"""

from pathlib import Path
import json
import shlex
import time
from datetime import datetime
import os
import uuid
from .logger import log_command
from ai import gaiservices
from ai import ai_prompt

STRUCT_FILE = Path(__file__).parent / "file_structure.txt"
DEFAULT_STRUCTURE_COMPACT = {
    "/": ["home", "etc", "var", "tmp"],
    "/home": ["asus"],
    "/home/asus": ["notes.txt", "secrets.txt"],
    "/home/asus/notes.txt": "These are sample notes.\nTry 'cat notes.txt'\n",
    "/home/asus/secrets.txt": "This file is an illusion.\n",
    "/etc/issue": "Ubuntu 20.04.6 LTS\n",
}

# --- helpers to load/save various structure shapes --- #
def load_structure():
    if not STRUCT_FILE.exists():
        save_structure_compact(DEFAULT_STRUCTURE_COMPACT)
        return normalize_structure_compact(DEFAULT_STRUCTURE_COMPACT)

    try:
        raw = json.loads(STRUCT_FILE.read_text(encoding="utf-8"))
    except Exception:
        # if broken, recreate default
        save_structure_compact(DEFAULT_STRUCTURE_COMPACT)
        return normalize_structure_compact(DEFAULT_STRUCTURE_COMPACT)

    # detect format
    if isinstance(raw, dict) and ("dirs" in raw or "files" in raw):
        # already in namespaced format
        dirs = raw.get("dirs", {})
        files = raw.get("files", {})
        # ensure types
        return {"dirs": {k: list(v) for k, v in dirs.items()}, "files": {k: str(v) for k, v in files.items()}, "mtimes": raw.get("mtimes", {})}
    else:
        # compact format (your sample)
        return normalize_structure_compact(raw)


def normalize_structure_compact(compact):
    """
    Convert compact structure into namespaced dict:
    { "dirs": { "/": [...], ... }, "files": { "/path/file": "content", ... }, "mtimes": {path: epoch, ...} }
    """
    dirs = {}
    files = {}
    mtimes = {}
    for k, v in compact.items():
        if isinstance(v, list):
            dirs[k.rstrip("/") if k != "/" else "/"] = list(v)
        else:
            # assume file with content
            files[k] = str(v)
            # set mtime to now (will be overridden if mtimes file exists)
            mtimes[k] = int(time.time())
    # ensure root exists
    if "/" not in dirs:
        dirs["/"] = []
    return {"dirs": dirs, "files": files, "mtimes": mtimes}


def save_structure(struct):
    """
    Save in namespaced format (dirs/files/mtimes).
    Use atomic temp file replace.
    """
    tmp = STRUCT_FILE.with_suffix(".tmp")
    data = {"dirs": struct["dirs"], "files": struct["files"], "mtimes": struct.get("mtimes", {})}
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STRUCT_FILE)


def save_structure_compact(compact):
    tmp = STRUCT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(compact, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STRUCT_FILE)


# formatting helpers
def _now_mtime_of_struct():
    """Fallback timestamp if specific mtime missing: use the structure file mtime."""
    try:
        ts = int(STRUCT_FILE.stat().st_mtime)
        return ts
    except Exception:
        return int(time.time())


def _format_mtime(epoch):
    dt = datetime.fromtimestamp(epoch)
    # PowerShell-like: MM/DD/YYYY hh:MM AM/PM
    return dt.strftime("%m/%d/%Y %I:%M %p")


def _mode_for(is_dir: bool):
    return "d-----" if is_dir else "-a----"


def _size_of(content: str):
    try:
        return len(content.encode("utf-8"))
    except Exception:
        return 0


# --- FakeShell class --- #
class FakeShell:
    def __init__(self, chan, addr: str, username: str, session_id: str = None):
        self.chan = chan
        self.addr = addr
        self.username = username
        # allow session_id to be supplied by the SSH server so connection/auth and command logs
        # can be correlated. If not provided, generate one locally.
        self.session_id = session_id if session_id else str(uuid.uuid4())[:8]
        self.env_home = f"/home/{username}"
        self.cwd = self.env_home
        self.struct = load_structure()  # normalized
        # ensure basic structure entries exist
        self.struct.setdefault("dirs", {})
        self.struct.setdefault("files", {})
        self.struct.setdefault("mtimes", {})
        self.command_history = []


    def _log(self, cmd: str, output: str = ""):
        """Log command execution - this is called for EVERY command"""
        try:
            log_command(self.addr, self.username, cmd, session_id=self.session_id, output=output)
        except Exception as e:
            # Don't let logging errors break the shell
            print(f"Logging error: {e}")

    def _normpath(self, path: str) -> str:
        """Expand ~, relative paths, ., .., return cleaned absolute path."""
        if not path:
            return self.cwd
        path = path.strip()
        if path.startswith("~"):
            path = path.replace("~", self.env_home, 1)
        if not path.startswith("/"):
            # relative; if cwd is a file (allowed), its parent is used
            base = self.cwd
            if base in self.struct["files"]:
                base = "/" + "/".join(base.strip("/").split("/")[:-1]) if "/" in base.strip("/") else "/"
            if base == "":
                base = "/"
            path = base.rstrip("/") + "/" + path
        parts = []
        for p in path.split("/"):
            if p == "" or p == ".":
                continue
            if p == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(p)
        return "/" + "/".join(parts) if parts else "/"

    def _is_dir(self, path: str) -> bool:
        p = path.rstrip("/") if path != "/" else "/"
        return p in self.struct["dirs"]

    def _is_file(self, path: str) -> bool:
        return path in self.struct["files"]

    def _dir_entries(self, path: str):
        p = path.rstrip("/") if path != "/" else "/"
        return list(self.struct["dirs"].get(p, []))

    def _register_dir(self, path: str):
        p = path.rstrip("/") if path != "/" else "/"
        if p not in self.struct["dirs"]:
            # ensure parents
            parent = "/" + "/".join(p.strip("/").split("/")[:-1]) if "/" in p.strip("/") else "/"
            if parent == "":
                parent = "/"
            if parent not in self.struct["dirs"]:
                # create parent recursively
                self._register_dir(parent)
            # add to parent listing
            name = p.rstrip("/").split("/")[-1]
            if name and name not in self.struct["dirs"].get(parent, []):
                self.struct["dirs"].setdefault(parent, []).append(name)
            self.struct["dirs"][p] = []

    
    def _unregister_dir(self, path: str):
        p = path.rstrip("/") if path != "/" else "/"
        if p in self.struct["dirs"]:
            # ensure empty
            if self.struct["dirs"].get(p):
                return False  # not empty
            # remove from parent
            parent = "/" + "/".join(p.strip("/").split("/")[:-1]) if "/" in p.strip("/") else "/"
            if parent == "":
                parent = "/"
            name = p.rstrip("/").split("/")[-1]
            if name in self.struct["dirs"].get(parent, []):
                self.struct["dirs"][parent].remove(name)
            del self.struct["dirs"][p]
            return True
        return False

    #working for AI-generated files into filesystem
    def _add_dynamic_file(self, filepath: str, content: str):
        """
        Helper to add a file to the virtual FS so 'ls' and 'cat' both work.
        """
        # 1. Normalize path
        filepath = self._normpath(filepath)
        
        # 2. Save Content (For 'cat')
        self.struct["files"][filepath] = content
        self.struct.setdefault("mtimes", {})[filepath] = int(time.time())
        
        # 3. Update Directory Listing (For 'ls') <--- THIS IS THE KEY PART
        parent = "/" + "/".join(filepath.strip("/").split("/")[:-1]) if "/" in filepath.strip("/") else "/"
        if parent == "": parent = "/"
        
        basename = filepath.rstrip("/").split("/")[-1]
        
        # Ensure parent dir exists
        if parent not in self.struct["dirs"]:
            self.struct["dirs"][parent] = []
            
        # Add filename to parent dir if not already there
        if basename not in self.struct["dirs"][parent]:
            self.struct["dirs"][parent].append(basename)
    
    async def _handle_hybrid_command(self, cmdline: str, target_name: str, prompt_instruction: str, is_dir: bool = False):
        """
        The Bridge Function.
        1. Registers the file/folder in Python (so 'ls' sees it).
        2. Asks AI for the realistic output (so user sees it).
        """
        # Update the Librarian (Python FS) ---
        # We process the path relative to current directory
        full_target_path = self._normpath(target_name)
        
        if is_dir:
            # It's a directory (like git clone)
            self._register_dir(full_target_path)
        else:
            # It's a file (like wget or touch)
            placeholder_content = f"Binary content or script for {target_name}.\nGenerated by command: {cmdline}"
            self._add_dynamic_file(full_target_path, placeholder_content)

        # We ask the AI specifically for the visual output of the command
        system_instruction = ai_prompt.get_system_prompt(
            username=self.username, 
            hostname="server", 
            cwd=self.cwd, 
            history=self.command_history
        )
        
        # We append a strict instruction to the prompt to ensure it mimics the specific tool
        full_prompt = (
            f"Simulate the exact text output of the command: '{cmdline}'.\n"
            f"{prompt_instruction}\n"
            "Do not explain. Output only the terminal text."
        )

        ai_output = await gaiservices.get_ai_response(system_instruction, full_prompt)
        
        return ai_output
    
    async def handle(self, cmdline: str):
        system_instruction = ai_prompt.get_system_prompt(
            username=self.username, 
            hostname="server",
            cwd=self.cwd,
            history=self.command_history
        )
        
        # Handle empty input
        if cmdline is None:
            return
        cmdline = cmdline.strip()
        if cmdline == "":
            self.chan.write("\r\n")
            return

        # Parse command
        parts = shlex.split(cmdline)
        if not parts:
            self.chan.write("\r\n")
            return
        cmd = parts[0]
        args = parts[1:]
        
        # Update command history
        if cmdline and cmdline.strip():
            self.command_history.append(cmdline)
            if len(self.command_history) > 10:
                self.command_history.pop(0)

        # ===== ai_test command =====
        if cmdline.startswith("ai_test"):
            prompt = cmdline[8:].strip()
            response = await gaiservices.get_ai_response(system_instruction, prompt)
            output = response if response else f"{cmd}: command not found"
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== exit/logout =====
        if cmd in ("exit", "logout"):
            output = "logout"
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            raise EOFError("exit requested")

        # ===== whoami =====
        if cmd == "whoami":
            output = self.username
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== cd =====
        if cmd == "cd":
            target = args[0] if args else "~"
            target_path = self._normpath(target)
            if self._is_dir(target_path) or self._is_file(target_path):
                self.cwd = target_path
                self.chan.write("\r\n")
                self._log(cmdline, f"SUCCESS: changed to {target_path}")  # LOG HERE
                return
            output = f"cd: {target}: No such file or directory"
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== mkdir =====
        if cmd == "mkdir":
            if len(args) == 0:
                output = "mkdir: missing operand"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            name = args[0]
            target_path = self._normpath(name)
            if self._is_dir(target_path) or self._is_file(target_path):
                output = f"mkdir: cannot create directory '{name}': File exists"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            self._register_dir(target_path)
            self.struct.setdefault("mtimes", {})[target_path] = int(time.time())
            save_structure(self.struct)
            self._log(cmdline, f"SUCCESS: created directory {target_path}")  # LOG HERE
            return

        # ===== rmdir =====
        if cmd == "rmdir":
            if len(args) == 0:
                output = "rmdir: missing operand"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            name = args[0]
            target_path = self._normpath(name)
            if not self._is_dir(target_path):
                output = f"rmdir: failed to remove '{name}': No such directory"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            if self.struct["dirs"].get(target_path):
                output = f"rmdir: failed to remove '{name}': Directory not empty"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            ok = self._unregister_dir(target_path)
            if not ok:
                output = f"rmdir: failed to remove '{name}'"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            save_structure(self.struct)
            self._log(cmdline, f"SUCCESS: removed directory {target_path}")  # LOG HERE
            return

        # ===== pwd =====
        if cmd == "pwd":
            output = self.cwd
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== ls =====
        if cmd == "ls":
            target = args[0] if args else "."
            target_path = self._normpath(target)
            
            if self._is_file(target_path):
                name = target_path.rstrip("/").split("/")[-1]
                is_dir = False
                mode = _mode_for(is_dir)
                mtime = self.struct.get("mtimes", {}).get(target_path, _now_mtime_of_struct())
                mtime_s = _format_mtime(mtime)
                size = _size_of(self.struct["files"].get(target_path, ""))
                line = f"{mode:<6} {mtime_s:<20} {str(size):>12} {name}"
                self.chan.write(line + "\r\n")
                self._log(cmdline, line)  # LOG HERE
                return
            
            if not self._is_dir(target_path):
                output = f"ls: cannot access '{target}': No such file or directory"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            
            entries = self._dir_entries(target_path)
            lines = []
            for e in sorted(entries):
                full = (target_path.rstrip("/") + "/" + e) if target_path != "/" else "/" + e
                is_dir = self._is_dir(full)
                mode = _mode_for(is_dir)
                mtime = self.struct.get("mtimes", {}).get(full, _now_mtime_of_struct())
                mtime_s = _format_mtime(mtime)
                if self._is_file(full):
                    size = _size_of(self.struct["files"].get(full, ""))
                    size_s = str(size)
                else:
                    size_s = ""
                lines.append(f"{mode:<6} {mtime_s:<20} {size_s:>12} {e}")
            
            if lines:
                for ln in lines:
                    self.chan.write(ln + "\r\n")
                output = "\n".join(lines)
            else:
                self.chan.write("\r\n")
                output = "(empty directory)"
            
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== cat =====
        if cmd == "cat":
            if not args:
                output = "cat: missing file operand"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            target = args[0]
            target_path = self._normpath(target)

            if not self._is_file(target_path):
                system_instruction = ai_prompt.get_system_prompt(self.username, "server")
                file_prompt = ai_prompt.get_file_content_prompt(target_path)
                
                generated_content = await gaiservices.get_ai_response(system_instruction, file_prompt)
                
                if not generated_content or "command not found" in generated_content.lower():
                    output = f"cat: {target}: No such file or directory"
                    self.chan.write(output + "\r\n")
                    self._log(cmdline, output)  # LOG HERE
                    return

                self._add_dynamic_file(target_path, generated_content)

            content = self.struct["files"].get(target_path, "")
            self.chan.write(content)
            if not content.endswith("\n"):
                self.chan.write("\r\n")
            # Log truncated content to avoid massive logs
            log_content = content[:500] + "..." if len(content) > 500 else content
            self._log(cmdline, log_content)  # LOG HERE
            return

        # ===== touch =====
        if cmd == "touch":
            if not args:
                output = "touch: missing file operand"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            name = args[0]
            target_path = self._normpath(name)
            
            if self._is_file(target_path):
                self.struct.setdefault("mtimes", {})[target_path] = int(time.time())
                save_structure(self.struct)
                self._log(cmdline, f"SUCCESS: updated mtime for {target_path}")  # LOG HERE
                return
            
            if self._is_dir(target_path):
                output = f"touch: cannot touch '{name}': Is a directory"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            
            self.struct["files"][target_path] = ""
            self.struct.setdefault("mtimes", {})[target_path] = int(time.time())
            parent = "/" + "/".join(target_path.strip("/").split("/")[:-1]) if "/" in target_path.strip("/") else "/"
            if parent == "":
                parent = "/"
            basename = target_path.rstrip("/").split("/")[-1]
            if parent not in self.struct["dirs"]:
                self._register_dir(parent)
            if basename not in self.struct["dirs"].get(parent, []):
                self.struct["dirs"].setdefault(parent, []).append(basename)
            save_structure(self.struct)
            self._log(cmdline, f"SUCCESS: created file {target_path}")  # LOG HERE
            return

        # ===== rm =====
        if cmd == "rm":
            if not args:
                output = "rm: missing operand"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            name = args[0]
            target_path = self._normpath(name)
            
            if not self._is_file(target_path):
                if self._is_dir(target_path):
                    output = f"rm: cannot remove '{name}': Is a directory"
                else:
                    output = f"rm: cannot remove '{name}': No such file or directory"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            
            del self.struct["files"][target_path]
            if target_path in self.struct.get("mtimes", {}):
                del self.struct["mtimes"][target_path]
            parent = "/" + "/".join(target_path.strip("/").split("/")[:-1]) if "/" in target_path.strip("/") else "/"
            if parent == "":
                parent = "/"
            basename = target_path.rstrip("/").split("/")[-1]
            if basename in self.struct["dirs"].get(parent, []):
                self.struct["dirs"][parent].remove(basename)
            save_structure(self.struct)
            self._log(cmdline, f"SUCCESS: removed file {target_path}")  # LOG HERE
            return

        # ===== clear =====
        if cmd == "clear":
            self.chan.write("\x1b[2J\x1b[H")
            self._log(cmdline, "SUCCESS: screen cleared")  # LOG HERE
            return

        # ===== uname =====
        if cmd == "uname":
            flag = args[0] if args else ""
            if flag == "-a":
                output = "Linux honeypot 5.15.0-89-generic #99-Ubuntu SMP Mon Oct 30 20:42:41 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
            else:
                output = "Linux"
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== id =====
        if cmd == "id":
            output = f"uid=1000({self.username}) gid=1000({self.username}) groups=1000({self.username})"
            self.chan.write(output + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== ps =====
        if cmd == "ps":
            lines = [
                "  PID TTY          TIME CMD",
                "    1 ?        00:00:01 systemd",
                "  123 ?        00:00:00 sshd",
                "  456 pts/0    00:00:00 bash"
            ]
            output = "\n".join(lines)
            for line in lines:
                self.chan.write(line + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== help =====
        if cmd == "help":
            lines = [
                "Available commands:",
                "  ls, cd, pwd, cat, echo, touch, rm, mkdir, rmdir",
                "  whoami, id, uname, ps, clear, help, exit"
            ]
            output = "\n".join(lines)
            for line in lines:
                self.chan.write(line + "\r\n")
            self._log(cmdline, output)  # LOG HERE
            return

        # ===== wget (HYBRID) =====
        if cmd == "wget":
            if not args:
                output = "wget: missing URL"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return
            
            url = args[0]
            filename = url.split("/")[-1] or "index.html"
            
            ai_output = await self._handle_hybrid_command(
                cmdline=cmdline,
                target_name=filename,
                prompt_instruction="Show a realistic wget progress bar [=====>] 100% and 'saved' message.",
                is_dir=False
            )
            
            if ai_output:
                self.chan.write(ai_output + "\r\n")
            self._log(cmdline, ai_output if ai_output else "ERROR: wget failed")  # LOG HERE
            return
        
        # ===== git clone (HYBRID) =====
        if cmd == "git" and (args and args[0] == "clone"):
            if len(args) < 2:
                output = "git clone: missing repository"
                self.chan.write(output + "\r\n")
                self._log(cmdline, output)  # LOG HERE
                return

            repo_url = args[1]
            folder_name = repo_url.split("/")[-1].replace(".git", "")
            
            ai_output = await self._handle_hybrid_command(
                cmdline=cmdline,
                target_name=folder_name,
                prompt_instruction="Show 'Cloning into...', object counting, and 'Resolving deltas'.",
                is_dir=True
            )
            
            if ai_output: 
                self.chan.write(ai_output + "\r\n")
            self._log(cmdline, ai_output if ai_output else "ERROR: git clone failed")  # LOG HERE
            return
        
        # ===== UNKNOWN COMMAND - AI FALLBACK =====
        ai_output = await gaiservices.get_ai_response(system_instruction, cmdline)
        
        if ai_output is not None:
            if ai_output.strip():
                self.chan.write(ai_output + "\r\n")
                self._log(cmdline, ai_output)  # LOG HERE
            else:
                self._log(cmdline, "(Silent AI output)")  # LOG HERE
        else:
            err_msg = f"{cmd}: command not found"
            self.chan.write(err_msg + "\r\n")
            self._log(cmdline, err_msg)  # LOG HERE
        return

    def prompt(self) -> str:
        return f"{self.username}@honeypot:{self.cwd}$ "