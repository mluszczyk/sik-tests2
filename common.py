import contextlib
import os
import socket
import configparser

BASE_DIR = os.path.dirname(__file__)

cp = configparser.ConfigParser()
cp.read([os.path.join(BASE_DIR, "defaults.cfg"), os.path.join(BASE_DIR, "config.cfg")])


@contextlib.contextmanager
def mock_client(port: int, proto=socket.SOCK_STREAM) -> socket.socket:
    with contextlib.closing(socket.socket(socket.AF_INET, proto)) as s:
        s.settimeout(WAIT_TIMEOUT)
        s.connect(("127.0.0.1", port))
        yield s


WAIT_TIMEOUT = 5  # never wait longer than this and raise exception
QUANTUM_SECONDS = 0.2
PLAYER_BOOT_SECONDS = 1
BINARY_PATH = cp.get("tests", "binary_path")
