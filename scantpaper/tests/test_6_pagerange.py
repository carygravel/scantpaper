"test pagerange widget"

from pagerange import PageRange


class SignalCatch:  # pylint: disable=too-few-public-methods
    "catch signal"

    def __init__(self):
        self.signal_emitted = False

    def catch_signal(self, _widget, _data):
        "catch signal"
        self.signal_emitted = True


def test_1():
    "test pagerange widget"
    prg = PageRange()
    assert isinstance(prg, PageRange), "Created PageRange widget"
    assert prg.active == "selected", "selected"

    prg2 = PageRange()
    assert prg2.get_active() == "selected", "selected2"

    prg2.set_active("all")
    assert prg2.get_active() == "all", "all"
    assert prg.get_active() == "all", "all2"


def test_signal():
    "test that changed signal is emitted"
    prg = PageRange()
    catcher = SignalCatch()
    prg.connect("changed", catcher.catch_signal)

    # change the value, signal should be emitted
    prg.set_active("all")
    assert catcher.signal_emitted, "Signal emitted"

    # reset the catcher
    catcher.signal_emitted = False

    # set to same value, signal should not be emitted
    prg.set_active("all")
    assert not catcher.signal_emitted, "Signal not emitted"
