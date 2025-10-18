# fake_shell.py
"""
Minimal FakeShell with PowerShell-like `ls` output.

Commands: ls, cd, whoami, mkdir, rmdir, exit

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
from logger import log_command

STRUCT_FILE = Path("file_structure.txt")
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
    def __init__(self, chan, addr: str, username: str):
        self.chan = chan
        self.addr = addr
        self.username = username
        self.session_id = str(uuid.uuid4())[:8]
        self.env_home = f"/home/{username}"
        self.cwd = self.env_home
        self.struct = load_structure()  # normalized
        # ensure basic structure entries exist
        self.struct.setdefault("dirs", {})
        self.struct.setdefault("files", {})
        self.struct.setdefault("mtimes", {})

    def _log(self, cmd: str):
        try:
            log_command(self.addr, self.username, cmd, session_id=self.session_id)
        except Exception:
            pass

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

    # command handlers
    async def handle(self, cmdline: str):
        self._log(cmdline)
        if cmdline is None:
            return
        cmdline = cmdline.strip()
        if cmdline == "":
            await self.chan.write("\r\n")
            return

        parts = shlex.split(cmdline)
        if not parts:
            await self.chan.write("\r\n")
            return
        cmd = parts[0]
        args = parts[1:]

        if cmd in ("exit", "logout"):
            await self.chan.write("logout\r\n")
            raise EOFError("exit requested")

        if cmd == "whoami":
            await self.chan.write(self.username + "\r\n")
            return

        if cmd == "cd":
            target = args[0] if args else "~"
            target_path = self._normpath(target)
            # If directory exists, cd there. If file exists, set cwd to file (as requested).
            if self._is_dir(target_path) or self._is_file(target_path):
                self.cwd = target_path
                return
            await self.chan.write(f"cd: {target}: No such file or directory\r\n")
            return

        if cmd == "mkdir":
            if len(args) == 0:
                await self.chan.write("mkdir: missing operand\r\n")
                return
            name = args[0]
            target_path = self._normpath(name)
            # if exists
            if self._is_dir(target_path) or self._is_file(target_path):
                await self.chan.write(f"mkdir: cannot create directory '{name}': File exists\r\n")
                return
            # create directory (and parents if needed permissively)
            self._register_dir(target_path)
            # persist mtimes entry
            self.struct.setdefault("mtimes", {})[target_path] = int(time.time())
            save_structure(self.struct)
            return

        if cmd == "rmdir":
            if len(args) == 0:
                await self.chan.write("rmdir: missing operand\r\n")
                return
            name = args[0]
            target_path = self._normpath(name)
            # must be a directory
            if not self._is_dir(target_path):
                await self.chan.write(f"rmdir: failed to remove '{name}': No such directory\r\n")
                return
            # must be empty
            if self.struct["dirs"].get(target_path):
                await self.chan.write(f"rmdir: failed to remove '{name}': Directory not empty\r\n")
                return
            ok = self._unregister_dir(target_path)
            if not ok:
                await self.chan.write(f"rmdir: failed to remove '{name}'\r\n")
                return
            # persist
            save_structure(self.struct)
            return

        if cmd == "ls":
            target = args[0] if args else "."
            target_path = self._normpath(target)
            # If target is file -> show single line with file name
            if self._is_file(target_path):
                name = target_path.rstrip("/").split("/")[-1]
                # build columns: Mode, LastWriteTime, Length, Name
                is_dir = False
                mode = _mode_for(is_dir)
                mtime = self.struct.get("mtimes", {}).get(target_path, _now_mtime_of_struct())
                mtime_s = _format_mtime(mtime)
                size = _size_of(self.struct["files"].get(target_path, ""))
                # align similar to PowerShell: Mode (6), LastWriteTime (20), Length (12 right), Name
                line = f"{mode:<6} {mtime_s:<20} {str(size):>12} {name}"
                await self.chan.write(line + "\r\n")
                return
            # If target is dir
            if not self._is_dir(target_path):
                await self.chan.write(f"ls: cannot access '{target}': No such file or directory\r\n")
                return
            entries = self._dir_entries(target_path)
            # For each entry, determine if dir or file and print columns
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
                    await self.chan.write(ln + "\r\n")
            else:
                await self.chan.write("\r\n")
            return

        # unknown
        await self.chan.write(f"{cmd}: command not found\r\n")
        return

    def prompt(self) -> str:
        return f"{self.username}@honeypot:{self.cwd}$ "
