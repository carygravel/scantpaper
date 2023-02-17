"test basethread class"
from basethread import BaseThread, Response, ResponseType
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class MyThread(BaseThread):
    "test thread class"

    def do_sum(self, arg1, arg2):
        "test method"
        return Response(
            type=ResponseType.FINISHED,
            process="sum",
            info=arg1 + arg2,
            uuid="",
            status=None,
        )


def finished_callback(result):
    "finished callback"
    assert result.info == 3, "basic two-way functionality"
    Gtk.main_quit()


def test_1():
    "test baseprocess class"
    thread = MyThread()
    thread.daemon = True
    thread.start()
    thread.send("sum", 1, 2, finished_callback=finished_callback)
    thread.send("quit")
    Gtk.main()
