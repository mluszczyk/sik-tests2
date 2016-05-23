import contextlib
import unittest
import subprocess


class Master(subprocess.Popen):
    def __init__(self, args=(), *, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL):
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
            line = program.communicate()[0]
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
