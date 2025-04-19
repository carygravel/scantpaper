"test pagerange widget"

from pagerange import PageRange


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
