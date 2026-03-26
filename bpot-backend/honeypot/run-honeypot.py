# run-honeypot.py
import asyncio
import asyncssh
import logging
from pathlib import Path
from .ssh_server import HoneypotSSHServer  # your SSH server class

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("honeypot")

HOST = "0.0.0.0"
PORT = 2222  # non-standard port
HOST_KEY_FILE = Path("ssh_host_key")


def ensure_host_key():
    """
    Check if host key exists; if not, generate a new RSA key.
    Handles asyncssh versions that may return bytes or str.
    """
    if HOST_KEY_FILE.exists():
        LOG.info("Host key exists: %s", HOST_KEY_FILE)
        return

    LOG.info("%s not found, generating a new RSA host key...", HOST_KEY_FILE)
    key = asyncssh.generate_private_key("ssh-rsa")

    # Export private key safely
    key_str = key.export_private_key()
    if isinstance(key_str, bytes):
        key_str = key_str.decode("utf-8")

    HOST_KEY_FILE.write_text(key_str, encoding="utf-8")
    LOG.info("Generated new host key at %s", HOST_KEY_FILE)


async def start_server():
    ensure_host_key()

    try:
        server = await asyncssh.create_server(
            lambda: HoneypotSSHServer(None),
            HOST,
            PORT,
            server_host_keys=[str(HOST_KEY_FILE)],
        )
        LOG.info("Honeypot listening on %s:%s", HOST, PORT)
        await server.wait_closed()
    except (OSError, asyncssh.Error) as exc:
        LOG.error("Failed to start server: %s", exc)


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        LOG.info("Shutting down")
