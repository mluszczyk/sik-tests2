import contextlib
import unittest
import subprocess
import unittest


class Master(subprocess.Popen):
    def __init__(self, args=(), *, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL):
        super().__init__(("../SK/radio-streaming/master",) + args, stdout=stdout, stderr=stderr)

@contextlib.contextmanager
def master_context(*args, **kwargs):
    program = Master(*args, **kwargs)
    yield program

    program.kill()
    program.wait()


class TestArguments(unittest.TestCase):
    def test_no_parameters(self):
        with master_context(()) as program:
            with self.assertRaises(subprocess.TimeoutExpired):
                line = program.communicate(timeout=1)[1]

    def test_one_parameter(self):
        with master_context(("50000",)) as program:
            with self.assertRaises(subprocess.TimeoutExpired):
                line = program.communicate(timeout=1)[1]

    def test_wrong_number(self):
        with master_context(("234", "234"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=1)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=1), 1)

    def test_not_a_number_suffix(self):
        with master_context(("234asdf",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=1)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=1), 1)

    def test_number_too_long(self):
        with master_context(("12345" * 10,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=1)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=1), 1)

    def test_not_a_number_at_all(self):
        with master_context(("ciastka",), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as program:
            line = program.communicate(timeout=1)[1]
            self.assertTrue(line)
            self.assertEqual(program.wait(timeout=1), 1)


if __name__ == '__main__':
    unittest.main()
