import contextlib
import socket
import subprocess
from unittest import TestCase

import time

from choose_port import choose_port
from common import QUANTUM_SECONDS, mock_client

PLAYER_PATH = "../zad2/Debug/player"


@contextlib.contextmanager
def player_context(port: int):
    proc = subprocess.Popen([PLAYER_PATH, "source", "/", "123", "-", str(port), "no"])
    yield proc
    proc.wait()


class TestPlayerRun(TestCase):
    def test_empty_parameters(self):
        proc = subprocess.Popen([PLAYER_PATH], stderr=subprocess.PIPE)
        ret = proc.wait()
        self.assertNotEqual(ret, 0)
        self.assertIn(b"usage", proc.stderr.read())

    def test_exit(self):
        port = choose_port()
        with player_context(port) as proc:
            time.sleep(QUANTUM_SECONDS)
            with mock_client(port, socket.SOCK_DGRAM) as client:
                client.send(b"QUIT\n")
            ret = proc.wait(5)
            self.assertEqual(ret, 0)
