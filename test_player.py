import contextlib
import os
import random
import socket
import string
import struct
import subprocess
import time
import unittest

from choose_port import choose_port
from common import (BINARY_PATH, PLAYER_BOOT_SECONDS, QUANTUM_SECONDS,
                    WAIT_TIMEOUT)

PLAYER_PATH = os.path.join(BINARY_PATH, "player")

class Player(subprocess.Popen):
    def __init__(self, args=(), *, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL):
        super().__init__((PLAYER_PATH,) + args, stdout=stdout, stderr=stderr)


@contextlib.contextmanager
def player_context(*args, **kwargs):
    program = Player(*args, **kwargs)
    time.sleep(QUANTUM_SECONDS)

    yield program

    program.kill()
    program.wait()

@contextlib.contextmanager
def streamer_server(*args, **kwargs):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    server_sock.bind((args[0][0], int(args[0][2])))
    server_sock.listen(1)

    with player_context(*args, **kwargs) as program:
        client_sock, client_addr = server_sock.accept()
        yield (client_sock, program)

        client_sock.close()

    server_sock.close()


class TestArguments(unittest.TestCase):
    def setUp(self):
        self.PARAMS = 6

        self.parameters = [
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "-", str(choose_port()), "yes"),
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "-", str(choose_port()), "no"),
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "test3.mp3", str(choose_port()), "no"),
            ("stream3.polskieradio.pl", "/", "8904", "-", str(choose_port()), "no"),
            ("localhost", "/", str(choose_port()), "-", str(choose_port()), "no"),
            ("localhost", "/", str(choose_port()), "-", str(choose_port()), "yes"),
            ("localhost", "/", str(choose_port()), "test3.mp3", str(choose_port()), "no"),
            ("localhost", "/", str(choose_port()), "test3.mp3", str(choose_port()), "yes"),
        ]

        self.wrong_parameters = [
            ["/", "sdfsdfa", "stream3.polskieradio."],
            ["/lol", "/w/"],
            ["89043284023823099", "-1", "0", "r", "65538", " "],
            ["",],
            ["502300124323423234", "wrr", "0", "-1", "65538", "", " "],
            ["tak", "nie", "", "-", "0", "1"],
        ]

    def test_valid(self):
        with player_context(self.parameters[3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            with self.assertRaises(subprocess.TimeoutExpired):
                self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_no_parameters(self):
        with player_context((), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_wrong_number_of_parameters(self):
        for num in range(0, self.PARAMS):
            tmp_parameters = tuple(self.parameters[0][0:num])
            with player_context(tmp_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                line = program.communicate(timeout=QUANTUM_SECONDS)[1]
                self.assertTrue(line)
                self.assertNotEqual(program.wait(timeout=QUANTUM_SECONDS), 0)

        for num in range(self.PARAMS + 1, self.PARAMS + 5):
            tmp_parameters = tuple(self.parameters[0][0:self.PARAMS]) + tuple(["0"] * (num - self.PARAMS))
            with player_context(tmp_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                line = program.communicate(timeout=QUANTUM_SECONDS)[1]
                self.assertTrue(line)
                self.assertNotEqual(program.wait(timeout=QUANTUM_SECONDS), 0)

    def test_wrong_parameters(self):
        valid_parameters = list(self.parameters[0])

        for num in range(0, self.PARAMS):
            for wrong_param in self.wrong_parameters[num]:
                tmp_parameters = valid_parameters.copy()
                tmp_parameters[num] = wrong_param

                with player_context(tuple(tmp_parameters), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                    line = program.communicate(timeout=QUANTUM_SECONDS)[1]
                    self.assertTrue(line)
                    self.assertNotEqual(program.wait(timeout=QUANTUM_SECONDS), 0)


    def test_quit_command(self):
        valid_parameters = self.parameters[1]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(WAIT_TIMEOUT)
            sock.sendto(b'QUIT', ('localhost', int(valid_parameters[4])))
            sock.close()

            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 0)


    def test_title_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(WAIT_TIMEOUT)
            sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))

            time.sleep(QUANTUM_SECONDS)

            response = sock.recvfrom(1000)
            sock.close()

            self.assertTrue(response[0])
            self.assertEqual(response[1], ('127.0.0.1', int(valid_parameters[4])))

    def test_title_command_with_custom_server(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')

            for _ in range(0, 10):
                sock.send(b'Z' * 16)
                sock.send(b'\x00')

            sock.send(b'Z' * 16)
            sock.send(b'\x02')
            sock.send(b"StreamTitle='title of the song';")

            for _ in range(0, 10):
                sock.send(b'Z' * 16)
                sock.send(b'\x00')

            command_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            command_sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))

            time.sleep(QUANTUM_SECONDS)

            response = command_sock.recvfrom(100)
            command_sock.close()

            self.assertIn(response[0], [b"title of the song", b"'title of the song'"])

    def test_no_meta_data(self):
        valid_parameters = self.parameters[1]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))
            response = sock.recvfrom(1000)
            sock.close()

            self.assertEqual(response[0], b'')
            self.assertEqual(response[1], ('127.0.0.1', int(valid_parameters[4])))

    def test_invalid_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(0, 10000):
                command = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(4, 6)))
                sock.sendto(bytes(command, 'utf-8'), ('127.0.0.1', int(valid_parameters[4])))

            sock.close()

            with self.assertRaises(subprocess.TimeoutExpired):
                self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 0)


    def test_spam_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(0, 10000):
                sock.sendto(b'PAUSE', ('127.0.0.1', int(valid_parameters[4])))
                sock.sendto(b'PLAY', ('127.0.0.1', int(valid_parameters[4])))
                sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))

            sock.close()

            with self.assertRaises(subprocess.TimeoutExpired):
                self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 0)


    def test_play_pause_command(self):
        valid_parameters = self.parameters[2]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(PLAYER_BOOT_SECONDS) # lepiej poczekac, bo dziwne akcje odwala...

            # sprawdzamy czy sie plik napelnia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(QUANTUM_SECONDS)
            self.assertNotEqual(size, os.path.getsize(valid_parameters[3]))

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'PAUSE', ('127.0.0.1', int(valid_parameters[4])))
            time.sleep(QUANTUM_SECONDS) # niech złapie komende

            # sprawdzamy czy plik przestal sie naplecia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(size, os.path.getsize(valid_parameters[3]))

            sock.sendto(b'PLAY', ('127.0.0.1', int(valid_parameters[4])))
            time.sleep(QUANTUM_SECONDS) # niech złapie komende

            # sprawdzamy czy znowu plik sie napelnia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(QUANTUM_SECONDS)
            self.assertNotEqual(size, os.path.getsize(valid_parameters[3]))

            sock.close()

            program.kill()
            program.wait()
            os.remove(valid_parameters[3])

    def test_timeout_response(self):
        valid_parameters = self.parameters[4]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            time.sleep(WAIT_TIMEOUT)

            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_invalid_response_streamer(self):
        valid_parameters = self.parameters[4]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            sock.send(b'ICY 404 OK\r\n')
            sock.send(b'\r\n')

            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_saving_data_without_meta(self):
        valid_parameters = self.parameters[6]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'\r\n')

            for _ in range(0, 1000):
                sock.send(b'Z' * 16)

            time.sleep(QUANTUM_SECONDS) # flush can take a while :C
            self.assertEqual(os.path.getsize(valid_parameters[3]), 16000)

            program.kill()
            program.wait()
            os.remove(valid_parameters[3])

    def test_saving_data_with_zerometa(self):
        valid_parameters = self.parameters[7]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')

            for _ in range(0, 1000):
                sock.send(((b'Z' * 16) + (b'\x00')))

            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(os.path.getsize(valid_parameters[3]), 16 * 1000)

            program.kill()
            program.wait()
            os.remove(valid_parameters[3])


    def test_saving_data_with_meta(self):
        valid_parameters = self.parameters[7]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')

            for _ in range(0, 1000):
                sock.send(((b'Z' * 16) + (b'\x02') + b"StreamTitle='title of the song';"))

            time.sleep(QUANTUM_SECONDS)
            self.assertEqual(os.path.getsize(valid_parameters[3]), 16 * 1000)

            program.kill()
            program.wait()
            os.remove(valid_parameters[3])

    def test_server_close_connection_when_header(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.close()
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_server_close_connection_when_sending_data(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')
            sock.send(b'Z' * 12)

            sock.close()
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 0)

    def test_server_close_connection_when_metadata(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')
            sock.send(b'Z' * 16)
            sock.send(b'\x50')
            sock.send(b"StreamTitle='title of the song';")

            sock.close()
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 0)


    def test_timeout_when_header(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            time.sleep(WAIT_TIMEOUT)

            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_timeout_when_sending_data(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')
            sock.send(b'Z' * 12)

            time.sleep(WAIT_TIMEOUT)

            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

    def test_timeout_when_metadata(self):
        valid_parameters = self.parameters[5]
        with streamer_server(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as (sock, program):
            sock.send(b'ICY 200 OK\r\n')
            sock.send(b'icy-metaint:16\r\n')
            sock.send(b'\r\n')
            sock.send(b'Z' * 16)
            sock.send(b'\x50')
            sock.send(b"StreamTitle='title of the song';")

            time.sleep(WAIT_TIMEOUT)

            line = program.communicate(timeout=QUANTUM_SECONDS)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=QUANTUM_SECONDS), 1)

if __name__ == '__main__':
    unittest.main(warnings='ignore')
