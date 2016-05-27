import contextlib
import socket


@contextlib.contextmanager
def mock_client(port: int, proto=socket.SOCK_STREAM) -> socket.socket:
    with contextlib.closing(socket.socket(socket.AF_INET, proto)) as s:
        s.settimeout(WAIT_TIMEOUT)
        s.connect(("127.0.0.1", port))
        yield s


WAIT_TIMEOUT = 5  # never wait longer than this and raise exception
QUANTUM_SECONDS = 0.2
