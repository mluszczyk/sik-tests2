import contextlib
import subprocess
import time
import unittest

from choose_port import choose_port
from common import mock_client, QUANTUM_SECONDS

PLAYER_HOSTNAME = b"localhost"


class Master(subprocess.Popen):
    def __init__(self, args=(), port=None, *, stdout=subprocess.PIPE, stderr=None):
        if port is not None:
            assert args == ()
            args = (str(port),)
        super().__init__(("../zad2/Debug/master",) + args, stdout=stdout, stderr=stderr)


@contextlib.contextmanager
def master_context(*args, **kwargs):
    program = Master(*args, **kwargs)
    yield program
    program.kill()
    program.wait()


class TestArguments(unittest.TestCase):
    def test_no_parameters(self):
        with master_context(()) as program:
            time.sleep(1)
        line = program.stdout.readline()
        self.assertTrue(line)

    def test_one_parameter(self):
        with master_context(("234",)) as program:
            line = program.communicate()[0]
            self.assertIn(b"234", line)

    def test_wrong_number(self):
        with master_context(("234", "234"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate()[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(), 1)

    def test_not_a_number_suffix(self):
        with master_context(("234asdf",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate()[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(), 1)

    def test_number_too_long(self):
        with master_context(("12345" * 10,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate()[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(), 1)

    def test_not_a_number_at_all(self):
        with master_context(("ciastka",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate()[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(), 1)


class TestCommands(unittest.TestCase):
    def test_wrong_command(self):
        port = choose_port()
        with master_context((str(port),), stderr=None, stdout=None):
            time.sleep(QUANTUM_SECONDS)
            with mock_client(port) as client:
                client.send(b"WRONG_COMMAND\n")
                line = client.recv(100)
                self.assertIn(b"ERROR", line)

                client.send(b"WRONG_COMMAND\n")
                line = client.recv(100)
                self.assertIn(b"ERROR", line)

    def test_start_wrong_host(self):
        port = choose_port()
        with master_context(port=port):
            time.sleep(QUANTUM_SECONDS)
            with mock_client(port) as client:
                client.send(b"START definitely_nonexistent 1 2 3 4 5 6\n")
                line = client.recv(100)
                self.assertIn(b"ERROR", line)


class TestIntegration(unittest.TestCase):

    def test_start(self):
        port = choose_port()
        with master_context(port=port):
            time.sleep(QUANTUM_SECONDS)
            with mock_client(port) as client:
                client.send(b"START %s params\n" % PLAYER_HOSTNAME)
                text = client.recv(100)
                ok, num_str = text.strip().split()
                self.assertEqual(ok, b"OK")
                client_num = int(num_str)
                time.sleep(QUANTUM_SECONDS)
                # TODO: assert that ssh was executed with correct parameters
                # TODO: assert that the client is still running
                client.send(b"QUIT %d\n" % client_num)
                time.sleep(QUANTUM_SECONDS)
                ok = client.recv(100)
                self.assertEqual(ok, b"OK %d\n" % client_num)
                # TODO: assert that the client has been stopped
                client.send(b"QUIT %d\n" % client_num)
                time.sleep(QUANTUM_SECONDS)
                text = client.recv(100)
                self.assertIn(b"ERROR", text)


if __name__ == '__main__':
    unittest.main()
