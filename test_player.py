import contextlib
import os
import random
import socket
import string
import subprocess
import time
import unittest


class Player(subprocess.Popen):
    def __init__(self, args=(), *, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL):
        super().__init__(("../SK/radio-streaming/player",) + args, stdout=stdout, stderr=stderr)


@contextlib.contextmanager
def player_context(*args, **kwargs):
    program = Player(*args, **kwargs)
    time.sleep(.01)

    yield program

    program.kill()
    program.wait()


class TestArguments(unittest.TestCase):
    def setUp(self):
        self.PARAMS = 6

        self.parameters = [
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "-", "50000", "yes"),
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "-", "50000", "no"),
            ("ant-waw-01.cdn.eurozet.pl", "/", "8602", "test3.mp3", "50000", "no"),
            ("stream3.polskieradio.pl", "/", "8904", "-", "32443", "no"),
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
                self.assertEqual(program.wait(timeout=1), 1)

    def test_no_parameters(self):
        with player_context((), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=1)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=1), 1)

    def test_wrong_number_of_parameters(self):
        for num in range(0, self.PARAMS):
            tmp_parameters = tuple(self.parameters[0][0:num])
            with player_context(tmp_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                line = program.communicate(timeout=1)[1]
                self.assertTrue(line)
                self.assertNotEqual(program.wait(timeout=1), 0)

        for num in range(self.PARAMS + 1, self.PARAMS + 5):
            tmp_parameters = tuple(self.parameters[0][0:self.PARAMS]) + tuple(["0"] * (num - self.PARAMS))
            with player_context(tmp_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                line = program.communicate(timeout=1)[1]
                self.assertTrue(line)
                self.assertNotEqual(program.wait(timeout=1), 0)

    def test_wrong_parameters(self):
        valid_parameters = list(self.parameters[0])

        for num in range(0, self.PARAMS):
            for wrong_param in self.wrong_parameters[num]:
                tmp_parameters = valid_parameters.copy()
                tmp_parameters[num] = wrong_param

                with player_context(tuple(tmp_parameters), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
                    line = program.communicate(timeout=1)[1]
                    self.assertTrue(line)
                    self.assertNotEqual(program.wait(timeout=1), 0)

    def test_quit_command(self):
        valid_parameters = self.parameters[1]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'QUIT', ('localhost', int(valid_parameters[4])))
            sock.close()

            self.assertEqual(program.wait(timeout=5), 0)

    def test_title_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))
            response = sock.recvfrom(1000)
            sock.close()

            self.assertTrue(response[0])
            self.assertEqual(response[1], ('127.0.0.1', int(valid_parameters[4])))

    def test_no_meta_data(self):
        valid_parameters = self.parameters[1]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))
            response = sock.recvfrom(1000)
            sock.close()

            self.assertEqual(response[0], b'')
            self.assertEqual(response[1], ('127.0.0.1', int(valid_parameters[4])))

    def test_invalid_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(0, 10000):
                command = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(4, 6)))
                sock.sendto(bytes(command, 'utf-8'), ('127.0.0.1', int(valid_parameters[4])))

            sock.close()

            with self.assertRaises(subprocess.TimeoutExpired):
                self.assertEqual(program.wait(timeout=1), 0)

    def test_spam_command(self):
        valid_parameters = self.parameters[0]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(0, 10000):
                sock.sendto(b'PAUSE', ('127.0.0.1', int(valid_parameters[4])))
                sock.sendto(b'PLAY', ('127.0.0.1', int(valid_parameters[4])))
                sock.sendto(b'TITLE', ('127.0.0.1', int(valid_parameters[4])))

            sock.close()

            with self.assertRaises(subprocess.TimeoutExpired):
                self.assertEqual(program.wait(timeout=1), 0)

    def test_play_pause_command(self):
        valid_parameters = self.parameters[2]

        with player_context(valid_parameters, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as program:
            time.sleep(1) # lepiej poczekac, bo dziwne akcje odwala...

            # sprawdzamy czy sie plik napelnia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(0.8)
            self.assertNotEqual(size, os.path.getsize(valid_parameters[3]))

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'PAUSE', ('127.0.0.1', int(valid_parameters[4])))
            time.sleep(0.1) # niech złapie komende

            # sprawdzamy czy plik przestal sie naplecia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(0.8)
            self.assertEqual(size, os.path.getsize(valid_parameters[3]))

            sock.sendto(b'PLAY', ('127.0.0.1', int(valid_parameters[4])))
            time.sleep(0.1) # niech złapie komende

            # sprawdzamy czy znowu plik sie napelnia
            size = os.path.getsize(valid_parameters[3])
            time.sleep(0.8)
            self.assertNotEqual(size, os.path.getsize(valid_parameters[3]))

            sock.close()

            program.kill()
            program.wait()
            os.remove(valid_parameters[3])

if __name__ == '__main__':
    unittest.main()
