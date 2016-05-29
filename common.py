import contextlib
import os
import socket
import configparser

BASE_DIR = os.path.dirname(__file__)

cp = configparser.ConfigParser()
cp.read([os.path.join(BASE_DIR, "defaults.cfg"), os.path.join(BASE_DIR, "config.cfg")])

class BufferedSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        self._buffer = b''
        socket.socket.__init__(self, *args, **kwargs)

    def readline(self):
        while b'\r\n' not in self._buffer:
            self._buffer += self.recv(100)
        newline_pos = self._buffer.find(b'\r\n')
        line = self._buffer[:newline_pos]
        self._buffer = self._buffer[newline_pos+2:]
        return line

@contextlib.contextmanager
def mock_client(port: int, proto=socket.SOCK_STREAM) -> BufferedSocket:
    with contextlib.closing(BufferedSocket(socket.AF_INET, proto)) as s:
        s.settimeout(WAIT_TIMEOUT)
        s.connect(("127.0.0.1", port))
        yield s


WAIT_TIMEOUT = 5  # never wait longer than this and raise exception
QUANTUM_SECONDS = 0.2
PLAYER_BOOT_SECONDS = 1
BINARY_PATH = cp.get("tests", "binary_path")
