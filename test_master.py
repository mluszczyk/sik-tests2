import contextlib
import os
import subprocess
import time
import unittest
from random import randint

from choose_port import choose_port
from common import mock_client, QUANTUM_SECONDS, BINARY_PATH, VALID_ARGS

PLAYER_HOSTNAME = b"localhost"
MASTER_PATH = os.path.join(BINARY_PATH, "master")


class Master(subprocess.Popen):
    def __init__(self, args=(), port=None, *, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        if port is not None:
            assert args == ()
            args = (str(port),)
        super().__init__((MASTER_PATH,) + args, stdout=stdout, stderr=stderr)


@contextlib.contextmanager
def master_context(*args, **kwargs):
    program = Master(*args, **kwargs)
    try:
        yield program
    finally:
        program.kill()
        program.wait()

@contextlib.contextmanager
def master_and_mock_client():
    port = choose_port()
    with master_context(port=port):
        time.sleep(QUANTUM_SECONDS)
        with mock_client(port) as client:
            yield client


class TestArguments(unittest.TestCase):
    def test_no_parameters(self):
        with master_context((), stdout=subprocess.PIPE) as program:
            time.sleep(QUANTUM_SECONDS)
        line = program.stdout.readline()
        self.assertTrue(line)
        self.assertNotIn(b"0", line.split())

    def test_one_parameter(self):
        with master_context(("50000",), stdout=subprocess.PIPE) as program:
            time.sleep(QUANTUM_SECONDS)
        line = program.stdout.readline()
        self.assertEqual(line, b'')

    def test_zero(self):
        with master_context(("0",), stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_wrong_number(self):
        with master_context(("234", "234"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_not_a_number_suffix(self):
        with master_context(("234asdf",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_number_too_long(self):
        with master_context(("12345" * 10,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_not_a_number_at_all(self):
        with master_context(("ciastka",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)


class TestCommands(unittest.TestCase):
    def assertOK(self, line):
        splited = line.split()
        self.assertEqual(len(splited), 2)
        self.assertEqual(splited[0], b"OK")
        return splited[1]

    def test_wrong_command(self):
        with master_and_mock_client() as client:
            client.send(b"WRONG_COMMAND\n")
            line = client.readline()
            self.assertIn(b"ERROR", line)

            client.send(b"WRONG_COMMAND\n")
            line = client.readline()
            self.assertIn(b"ERROR", line)

    def test_start_wrong_host(self):
        with master_and_mock_client() as client:
            client.send(b"START definitely_nonexistent 1 2 3 4 5 6\n")
            line = client.readline()
            self.assertIn(b"ERROR", line)

    def test_start(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"START %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertOK(client.readline())

    def test_start_with_large_spaces(self):
        with master_and_mock_client() as client:
            args = bytes("     ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"START   %s   %s\n" % (PLAYER_HOSTNAME, args))
            self.assertOK(client.readline())

    def test_quit(self):
        with master_and_mock_client() as client:
            args = bytes("     ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"START   %s   %s\n" % (PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())
            client.send(b"QUIT %s\n" % player_id)
            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(subprocess.check_output(["pidof", "player"]), b"")

    def test_telnet_control_sequences(self):
        sequences = (b"\xff\xfe\x06", b"\xff\xf5", b"\xff\xf7")
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            for seq in sequences:
                index = randint(0, len(args))
                args = args[0:index] + seq + args[index:]
            client.send(b"START %s %s\n" % (PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())

    def test_client_crash(self):
        if PLAYER_HOSTNAME != b"localhost":
            return
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"START %s %s\n" % (PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())
            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(subprocess.call(["killall", "player"]), 0)
            line = client.readline()
            self.assertTrue(line.startswith(b"ERROR %s" % player_id))


class TestIntegration(unittest.TestCase):

    def test_start(self):
        port = choose_port()
        with master_context(port=port):
            time.sleep(QUANTUM_SECONDS)
            with mock_client(port) as client:
                client.send(b"START %s p1 p2 p3 p4 p5 p6\n" % PLAYER_HOSTNAME)
                text = client.readline()
                # Not finished yet
                # ok, num_str = text.strip().split()
                # self.assertEqual(ok, b"OK")
                # client_num = int(num_str)
                # time.sleep(QUANTUM_SECONDS)
                # # TODO: assert that ssh was executed with correct parameters
                # # TODO: assert that the client is still running
                # client.send(b"QUIT %d\n" % client_num)
                # time.sleep(QUANTUM_SECONDS)
                # ok = client.readline()
                # self.assertEqual(ok, b"OK %d\n" % client_num)
                # # TODO: assert that the client has been stopped


if __name__ == '__main__':
    if PLAYER_HOSTNAME != b"localhost":
        print("========================================")
        print("Some tests require you to launch players on localhost.")
        print("They will be ignored if you won't be doing so.")
        print("========================================")
    unittest.main(warnings='ignore')
