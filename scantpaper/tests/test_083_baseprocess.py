"test baseprocess class"
from baseprocess import BaseProcess


class MyProcess(BaseProcess):
    "test process class"

    def do_sum(self, arg1, arg2):
        "test method"
        return arg1 + arg2


def test_1():
    "test baseprocess class"
    process = MyProcess()
    process.start()
    process.send("sum", 1, 2)
    assert process.responses.get() == 3, "basic two-way functionality"
    process.send("quit")
