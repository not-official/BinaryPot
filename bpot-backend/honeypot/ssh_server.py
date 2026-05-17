# ssh_server.py
import asyncio
import asyncssh
import logging
import uuid
import requests


from .logger import log_connection
from .fake_shell import FakeShell




LOG = logging.getLogger(__name__)


API_URL = "http://127.0.0.1:8000"




class HoneypotSSHServer(asyncssh.SSHServer):
    def __init__(self, peername):
        self.peername = peername
        self.session_id = None
        self.username = None
        super().__init__()


    def connection_made(self, conn):
        peer = conn.get_extra_info("peername")
        LOG.info(f"Connection from {peer}")
        self.peername = peer


        try:
            self.session_id = str(uuid.uuid4())[:8]
        except Exception:
            self.session_id = None


        try:
            requests.post(
                f"{API_URL}/session/start",
                json={
                    "session_id": self.session_id,
                    "remote_addr": self.peername[0] if self.peername else "unknown",
                    "username": self.username or "unknown",
                },
                timeout=2,
            )
        except Exception as e:
            LOG.error(f"FastAPI session start failed: {e}")


    def connection_lost(self, exc):
        ip = self.peername[0] if self.peername else "unknown"


        log_connection(
            ip,
            getattr(self, "username", None),
            None,
            event="auth_termination",
            session_id=self.session_id,
        )


        try:
            requests.post(
                f"{API_URL}/session/end",
                json={"session_id": self.session_id},
                timeout=2,
            )
        except Exception as e:
            LOG.error(f"FastAPI session end failed: {e}")


        LOG.info("Connection lost")


    def begin_auth(self, username):
        self.username = username
        return True


    def password_auth_supported(self):
        return True


    async def validate_password(self, username, password):
        ip = self.peername[0] if self.peername else "unknown"


        log_connection(
            ip,
            username,
            password,
            event="auth_attempt",
            session_id=self.session_id,
        )


        log_connection(
            ip,
            username,
            password,
            event="auth_success",
            session_id=self.session_id,
        )


        return True


    def session_requested(self):
        return HoneypotSSHSession(
            self.peername,
            session_id=self.session_id,
            username=self.username,
        )




class HoneypotSSHSession(asyncssh.SSHServerSession):
    def __init__(self, peername, session_id=None, username=None):
        self._chan = None
        self._addr = peername[0] if peername else "unknown"
        self._username = username or "unknown"
        self._shell = None
        self._session_id = session_id


        self._input_buffer = ""
        self._last_was_cr = False
        self._escape_state = 0


        # set = input allowed, clear = command/AI is running
        self._idle = asyncio.Event()
        self._idle.set()


    # --------------------------------------------------------
    # Pause/resume SSH input while command/AI is running
    # --------------------------------------------------------


    def _pause_input(self):
        self._idle.clear()


        try:
            self._chan.pause_reading()
        except Exception:
            pass


    def _resume_input(self):
        try:
            self._chan.resume_reading()
        except Exception:
            pass


        self._idle.set()


    # --------------------------------------------------------
    # AsyncSSH callbacks
    # --------------------------------------------------------


    def connection_made(self, chan):
        self._chan = chan


        LOG.info(f"Session opened for {self._username} from {self._addr}")


        self._shell = FakeShell(
            self._chan,
            self._addr,
            self._username,
            session_id=self._session_id,
        )


        self._chan.write(
            "Welcome to Ubuntu 20.04.6 LTS "
            "(GNU/Linux 5.15.0-xyz x86_64)\r\n"
        )
        self._chan.write("Last login: some time ago on pts/0\r\n\r\n")
        self._chan.write(self._shell.prompt())


    def shell_requested(self):
        return True


    def pty_requested(self, term_type, term_size, term_modes):
        return True


    def exec_requested(self, command):
        if not self._idle.is_set():
            return False


        self._pause_input()
        asyncio.get_event_loop().create_task(self._handle_exec(command))
        return True


    async def _handle_exec(self, command):
        try:
            await self._shell.handle(command)
        except EOFError:
            pass
        finally:
            try:
                self._chan.write_eof()
                self._chan.exit(0)
            except Exception:
                pass


    def data_received(self, data, datatype):
        if not self._idle.is_set():
            return


        try:
            text = data.decode() if isinstance(data, (bytes, bytearray)) else data
        except Exception:
            text = str(data)


        for char in text:
            # Swallow escape sequences, e.g. arrow keys
            if self._escape_state == 1:
                self._escape_state = 2 if char == "[" else 0
                continue


            if self._escape_state == 2:
                if char.isalpha() or char == "~":
                    self._escape_state = 0
                continue


            # Avoid double-processing CRLF
            if self._last_was_cr:
                self._last_was_cr = False
                if char == "\n":
                    continue


            # ENTER
            if char in ("\r", "\n"):
                if char == "\r":
                    self._last_was_cr = True


                cmd_line = self._input_buffer.strip()
                self._input_buffer = ""


                # IMPORTANT:
                # Do NOT write "\r\n" here.
                # The SSH client already moves to the next line after Enter.
                # Writing another newline here creates the unwanted blank gap.


                if not cmd_line:
                    # Empty Enter should simply show prompt on the next line.
                    self._chan.write(self._shell.prompt())
                    continue


                self._pause_input()
                asyncio.get_event_loop().create_task(self._run_command(cmd_line))
                continue


            # BACKSPACE / DELETE
            if char in ("\x7f", "\b"):
                if self._input_buffer:
                    self._input_buffer = self._input_buffer[:-1]


                # Do not manually echo backspace.
                # The SSH client already handles visible input.
                continue


            # CTRL+C
            if char == "\x03":
                self._input_buffer = ""
                self._chan.write("^C\r\n")
                self._chan.write(self._shell.prompt())
                continue


            # CTRL+D
            if char == "\x04":
                try:
                    self._chan.write_eof()
                    self._chan.exit(0)
                except Exception:
                    pass
                continue


            # ESC
            if char == "\x1b":
                self._escape_state = 1
                continue


            # TAB ignored
            if char == "\t":
                continue


            # Normal printable character:
            # Store only. Do not echo, or the command appears twice.
            self._input_buffer += char


    async def _run_command(self, command):
        try:
            await self._shell.handle(command)


        except EOFError:
            try:
                self._chan.write_eof()
                self._chan.exit(0)
            except Exception:
                pass
            return


        except Exception as e:
            LOG.error(f"Command execution failed: {e}")


            try:
                self._chan.write(f"error: {e}\r\n")
            except Exception:
                pass


        try:
            self._chan.write("\r\n" + self._shell.prompt())
        except Exception:
            pass


        self._resume_input()


    def eof_received(self):
        return False


    def connection_lost(self, exc):
        LOG.info(f"Session closed for {self._username}")

