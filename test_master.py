
import contextlib
import os
import subprocess
import time
import unittest
import datetime
from random import randint

from choose_port import choose_port
from common import mock_client, QUANTUM_SECONDS, BINARY_PATH, VALID_ARGS, LONG_PAUSE

PLAYER_HOSTNAME = b"localhost"
MASTER_PATH = os.path.join(BINARY_PATH, "master")
SKIP_LONG_TESTS = False


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
        split = line.split()
        self.assertEqual(len(split), 2)
        self.assertEqual(split[0], b"OK")
        return split[1]

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
            last_idx = 0
            for seq in sequences:
                index = randint(last_idx, len(args))
                args = args[0:index] + seq + args[index:]
                last_idx = index + len(seq)
            client.send(b"START %s %s\n" % (PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())

    @unittest.skipIf(PLAYER_HOSTNAME != b"localhost", "Requires execution on localhost")
    def test_client_crash(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"START %s %s\n" % (PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())
            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(subprocess.call(["killall", "player"]), 0)
            line = client.readline()
            self.assertTrue(line.startswith(b"ERROR %s" % player_id))

    def test_at_command(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 21.12 100 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertOK(client.readline())

    def test_at_negative_duration(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 21.12 -1 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    def test_at_invalid_time(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 24.12 10 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    def test_at_invalid_time2(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 1.62 10 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    def test_at_invalid_time3(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT a1.32 10 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    def test_at_invalid_time4(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 1:22 10 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    def test_at_invalid_time5(self):
        with master_and_mock_client() as client:
            args = bytes(" ".join(VALID_ARGS()[8]), "utf-8")
            client.send(b"AT 1.a22 10 %s %s\n" % (PLAYER_HOSTNAME, args))
            self.assertTrue(client.readline().startswith(b"ERROR"))

    @unittest.skipIf(SKIP_LONG_TESTS, "Long test")
    @unittest.skipIf(PLAYER_HOSTNAME != b"localhost", "Requires execution on localhost")
    def test_at(self):
        with master_and_mock_client() as client:
            arg_list = VALID_ARGS()[8]
            output_path = os.path.expanduser(os.path.join("~", arg_list[3]))
            if os.path.exists(output_path):
                os.remove(output_path)

            # Launch client
            now = datetime.datetime.now()
            starttime = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) + \
                    datetime.timedelta(minutes=1)
            time_str = b"%d.%d" % (starttime.hour, starttime.minute)
            args = bytes(" ".join(arg_list), "utf-8")
            client.send(b"AT %s 10 %s %s\n" % (time_str, PLAYER_HOSTNAME, args))
            player_id = self.assertOK(client.readline())
            to_wait = starttime - now
            to_wait_s = int(to_wait.seconds + (to_wait.microseconds / 1e6) + 2)

            if to_wait_s > 5:
                client.send(b"PAUSE %s\n" % player_id)
                response = client.readline()
                self.assertTrue(response.startswith(b"ERROR %s" % player_id))
            else:
                print("\nIgnoring some tests, because there's not enough wait time")

            print("")
            while to_wait_s > 0:
                print("Waiting %d         \r" % to_wait_s, end="")
                time.sleep(1)
                to_wait_s -= 1
            print("Running                ")
            self.assertTrue(os.path.exists(output_path))

            # Check it's filling up
            initial_size = os.path.getsize(output_path)
            time.sleep(LONG_PAUSE)
            size = os.path.getsize(output_path)
            self.assertTrue(size > initial_size)

            # Check PAUSE works
            client.send(b"PAUSE %s\n" % player_id)
            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(self.assertOK(client.readline()), player_id)
            initial_size= os.path.getsize(output_path)
            time.sleep(LONG_PAUSE)
            size = os.path.getsize(output_path)
            self.assertEqual(size, initial_size)

            # Check PLAY works
            initial_size = os.path.getsize(output_path)
            client.send(b"PLAY %s\n" % player_id)
            time.sleep(LONG_PAUSE)
            self.assertEqual(self.assertOK(client.readline()), player_id)
            size = os.path.getsize(output_path)
            self.assertTrue(size > initial_size)

            # Check QUIT works
            initial_size = os.path.getsize(output_path)
            client.send(b"QUIT %s\n" % player_id)
            self.assertEqual(self.assertOK(client.readline()), player_id)
            time.sleep(LONG_PAUSE)
            self.assertEqual(subprocess.check_output(["pidof", "player"]), b"")


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
