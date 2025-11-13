# ssh_server.py
import asyncio
import asyncssh
import logging
import socket
import uuid
from logger import log_connection
from fake_shell import FakeShell

LOG = logging.getLogger(__name__)

class HoneypotSSHServer(asyncssh.SSHServer):
    def __init__(self, peername):
        self.peername = peername
        self.session_id = None
        super().__init__()

    def connection_made(self, conn):
        peer = conn.get_extra_info('peername')
        LOG.info(f"Connection from {peer}")
        self.peername = peer
        # generate a session id for this connection so auth and commands can be correlated
        try:
            self.session_id = str(uuid.uuid4())[:8]
        except Exception:
            self.session_id = None

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
        # include session_id so we can correlate auth attempts with session command logs
        log_connection(ip, username, password, event="auth_attempt", session_id=getattr(self, "session_id", None))
        # Accept all auth to lure activity
        return True

    def session_requested(self):
        # return a session handler instance
        return HoneypotSSHSession(self.peername, getattr(self, "session_id", None))

class HoneypotSSHSession(asyncssh.SSHServerSession):
    def __init__(self, peername, session_id=None):
        self._chan = None
        self._addr = peername[0] if peername else "unknown"
        self._username = None
        self._shell = None
        self._session_id = session_id

    def connection_made(self, chan):
        self._chan = chan
        self._username = chan.get_extra_info("username") or "unknown"
        LOG.info(f"Session opened for {self._username} from {self._addr}")
        # initialize fake shell
        self._shell = FakeShell(self._chan, self._addr, self._username, session_id=self._session_id)
        # write a fake banner
        self._chan.write("Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.15.0-xyz x86_64)\r\n")
        self._chan.write(f"Last login: some time ago on pts/0\r\n\r\n")
        self._chan.write(self._shell.prompt())

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
            # Skip the trailing empty string that results from text ending with \n
            if line == "" and i == len(lines) - 1:
                continue
            if line == "":
                # user pressed Enter with empty line (not trailing split artifact)
                self._chan.write("\r\n" + self._shell.prompt())
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
                # add blank line and show prompt with current directory
                self._chan.write("\r\n" + self._shell.prompt())

            asyncio.get_event_loop().create_task(run_and_prompt(line))

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        LOG.info("Session closed")
