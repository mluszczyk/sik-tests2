import itertools
from random import randint

FIRST_PORT = randint(30000, 40000)
port_iterable = itertools.count(FIRST_PORT)


def choose_port():
    return next(port_iterable)
