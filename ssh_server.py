# ssh_server.py
import asyncio
import asyncssh
import logging
import socket
from logger import log_connection
from fake_shell import FakeShell

LOG = logging.getLogger(__name__)

class HoneypotSSHServer(asyncssh.SSHServer):
    def __init__(self, peername):
        self.peername = peername
        super().__init__()

    def connection_made(self, conn):
        peer = conn.get_extra_info('peername')
        LOG.info(f"Connection from {peer}")
        self.peername = peer

    def connection_lost(self, exc):
        LOG.info("Connection lost")

    def begin_auth(self, username):
        # allow password authentication
        return True

    def password_auth_supported(self):
        return True

    async def validate_password(self, username, password):
        # Accept any password but log it
        ip = self.peername[0] if self.peername else "unknown"
        log_connection(ip, username, password, event="auth_attempt")
        # Accept all auth to lure activity
        return True

    def session_requested(self):
        # return a session handler instance
        return HoneypotSSHSession(self.peername)

class HoneypotSSHSession(asyncssh.SSHServerSession):
    def __init__(self, peername):
        self._chan = None
        self._addr = peername[0] if peername else "unknown"
        self._username = None
        self._shell = None

    def connection_made(self, chan):
        self._chan = chan
        self._username = chan.get_extra_info("username") or "unknown"
        LOG.info(f"Session opened for {self._username} from {self._addr}")
        # initialize fake shell
        self._shell = FakeShell(self._chan, self._addr, self._username)
        # write a fake banner
        self._chan.write("Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.15.0-xyz x86_64)\n")
        self._chan.write(f"Last login: some time ago on pts/0\n")
        self._chan.write(f"{self._username}@honeypot:~$ ")

    def shell_requested(self):
        return True

    def exec_requested(self, command):
        # if client requested non-interactive exec, handle by running one command
        asyncio.get_event_loop().create_task(self._handle_exec(command))
        return True

    async def _handle_exec(self, command):
        try:
            await self._shell.handle(command)
        except EOFError:
            pass
        finally:
            self._chan.write_eof()
            self._chan.exit(0)

    def data_received(self, data, datatype):
        # data contains bytes; convert to str and handle newline-terminated commands
        try:
            text = data.decode() if isinstance(data, (bytes, bytearray)) else data
        except Exception:
            text = data

        # buffer per newline - simple implementation:
        # assume user types commands terminated by \n or \r\n
        lines = text.replace("\r", "").split("\n")
        # if last chunk doesn't end with \n, the last element will be '', ignore partial handling for simplicity
        for i, line in enumerate(lines):
            if i == len(lines) - 1 and text and not text.endswith("\n"):
                # partial input: write it back as prompt input
                self._chan.write(line)
                continue
            if line == "":
                # user pressed Enter with empty line
                self._chan.write("\r\n" + f"{self._username}@honeypot:~$ ")
                continue
            # process full command
            async def run_and_prompt(cmd_line):
                try:
                    await self._shell.handle(cmd_line)
                except EOFError:
                    # close session
                    try:
                        self._chan.write_eof()
                        self._chan.exit(0)
                    except Exception:
                        pass
                    return
                # show prompt
                self._chan.write(f"{self._username}@honeypot:~$ ")

            asyncio.get_event_loop().create_task(run_and_prompt(line))

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        LOG.info("Session closed")
