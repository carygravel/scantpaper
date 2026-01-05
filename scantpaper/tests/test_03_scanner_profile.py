"test scanner option profiles"

import copy
import unittest.mock
import pytest
from scanner.profile import Profile, _synonyms
from frontend import enums


def test_synonyms():
    "test synonyms"
    assert _synonyms("page-height") == [
        "page-height",
        "pageheight",
    ], "synonyms for SANE_NAME_PAGE_HEIGHT"
    assert _synonyms("pageheight") == [
        "page-height",
        "pageheight",
    ], "synonyms for pageheight"
    assert _synonyms("page-width") == [
        "page-width",
        "pagewidth",
    ], "synonyms for SANE_NAME_PAGE_WIDTH"
    assert _synonyms("pagewidth") == [
        "page-width",
        "pagewidth",
    ], "synonyms for pagewidth"
    assert _synonyms("tl-x") == ["tl-x", "l"], "synonyms for SANE_NAME_SCAN_TL_X"
    assert _synonyms("l") == ["tl-x", "l"], "synonyms for l"
    assert _synonyms("tl-y") == ["tl-y", "t"], "synonyms for SANE_NAME_SCAN_TL_Y"
    assert _synonyms("t") == ["tl-y", "t"], "synonyms for t"
    assert _synonyms("br-x") == ["br-x", "x"], "synonyms for SANE_NAME_SCAN_BR_X"
    assert _synonyms("x") == ["br-x", "x"], "synonyms for x"
    assert _synonyms("br-y") == ["br-y", "y"], "synonyms for SANE_NAME_SCAN_BR_Y"
    assert _synonyms("y") == ["br-y", "y"], "synonyms for y"
    assert _synonyms("none") == ["none"], "no synonyms"


def test_profile_basic():
    "test basic Profile functionality"
    profile = Profile()
    assert isinstance(profile, Profile)
    profile.add_backend_option("y", "297")
    assert profile.get() == {
        "backend": [("y", "297")],
        "frontend": {},
    }, "basic functionality add_backend_option"

    profile.add_backend_option("br-y", "297")
    assert profile.get() == {
        "backend": [("br-y", "297")],
        "frontend": {},
    }, "pruned duplicate"


def test_frontend_options():
    "test frontend options"
    profile = Profile()
    profile.add_frontend_option("num_pages", 0)
    assert profile.get() == {
        "backend": [],
        "frontend": {"num_pages": 0},
    }, "basic functionality add_frontend_option"

    itr = profile.each_frontend_option()
    assert next(itr) == "num_pages", "basic functionality each_frontend_option"
    assert (
        profile.get_frontend_option("num_pages") == 0
    ), "basic functionality get_frontend_option"
    with pytest.raises(StopIteration):
        next(itr)

    profile.remove_frontend_option("num_pages")
    assert "num_pages" not in profile.frontend
    profile.remove_frontend_option("non-existent")  # Should not raise


def test_profile_init_data():
    "test Profile initialization from data"
    profile = Profile(frontend={"num_pages": 1}, backend=[("br-x", "297")])
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "basic functionality new_from_data"

    profile = Profile({"frontend": {"num_pages": 1}, "backend": [("br-x", "297")]})
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "basic functionality new_from_data with dict"

    profile = Profile(frontend={"num_pages": 1}, backend=[{"br-x": "297"}])
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "map old pre-v3 profiles to use tuples"

    # __init__ with dict but no "frontend" key
    p_no_front = Profile({"some": "other"})
    assert p_no_front.frontend == {"some": "other"}

    # __init__ with num_pages as string
    p1 = Profile(frontend={"num_pages": "5"})
    assert p1.frontend["num_pages"] == 5


def test_map_from_cli():
    "test map_from_cli"
    profile = Profile(backend=[("l", 1), ("y", 50), ("x", 50), ("t", 2)])
    assert profile.get() == {
        "backend": [("tl-x", 1), ("br-y", 52), ("br-x", 51), ("tl-y", 2)],
        "frontend": {},
    }, "basic functionality map_from_cli"

    # map_from_cli x/y without l/t
    p3 = Profile(backend=[("x", 10), ("y", 20)])
    assert p3.get_option_by_name("br-x") == 10
    assert p3.get_option_by_name("br-y") == 20


def test_backend_option_iteration():
    "test each_backend_option"
    profile = Profile(backend=[("tl-x", 1), ("br-y", 52), ("br-x", 51), ("tl-y", 2)])
    itr = profile.each_backend_option()
    assert next(itr) == 0, "basic functionality each_backend_option"
    assert profile.get_backend_option_by_index(0) == (
        "tl-x",
        1,
    ), "basic functionality get_backend_option_by_index"
    for _ in range(1, 4):
        next(itr)
    with pytest.raises(StopIteration):
        next(itr)

    itr = profile.each_backend_option(True)
    assert next(itr) == 3, "basic functionality each_backend_option reverse"
    for _ in range(1, 4):
        next(itr)
    with pytest.raises(StopIteration):
        next(itr)


def test_remove_backend_option():
    "test removal of backend options"
    profile = Profile(backend=[("tl-x", 1), ("br-y", 52), ("br-x", 51), ("tl-y", 2)])
    profile.remove_backend_option_by_name("tl-x")
    assert profile.get() == {
        "backend": [("br-y", 52), ("br-x", 51), ("tl-y", 2)],
        "frontend": {},
    }, "basic functionality remove_backend_option_by_name"

    profile.remove_backend_option_by_index(0)
    assert profile.num_backend_options() == 2
    assert profile.get_backend_option_by_index(0) == ("br-x", 51)

    # remove_backend_option_by_name not found - list not empty
    profile.remove_backend_option_by_name("non-existent")
    assert profile.num_backend_options() == 1
    assert profile.get_backend_option_by_index(0) == ("br-x", 51)

    # remove_backend_option_by_name - empty list
    p_empty = Profile()
    with pytest.raises(TypeError):
        p_empty.remove_backend_option_by_name("any")


def test_profile_magic_methods():
    "test magic methods"
    p1 = Profile(frontend={"num_pages": 5})
    p2 = copy.copy(p1)
    assert p1 == p2
    assert p1 is not p2

    s = str(p1)
    assert "Profile(frontend=" in s
    assert "backend=[]" in s

    assert p1 != Profile(frontend={"num_pages": 6})
    assert p1 != Profile(backend=[("opt", 1)])
    assert p1 != Profile(frontend=p1.frontend, backend=[("opt", 1)])


def test_add_backend_option_logic():
    "test add_backend_option logic and errors"
    p1 = Profile()
    # add_backend_option oldval logic
    p1.add_backend_option("opt1", 10, oldval=10)
    assert p1.num_backend_options() == 0

    # add_backend_option error handling
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_backend_option(None, 1)
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_backend_option("", 1)


def test_add_frontend_option_errors():
    "test add_frontend_option errors"
    p1 = Profile()
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_frontend_option(None, 1)
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_frontend_option("", 1)


def test_map_to_cli():
    "test map_to_cli"
    p4 = Profile(
        backend=[("tl-x", 1), ("tl-y", 2), ("br-x", 11), ("br-y", 12), ("other", 5)]
    )
    options = unittest.mock.Mock()
    options.by_name.return_value = {"type": enums.TYPE_INT}
    p5 = p4.map_to_cli(options)
    assert p5.get_option_by_name("l") == 1
    assert p5.get_option_by_name("t") == 2
    assert p5.get_option_by_name("x") == 10
    assert p5.get_option_by_name("y") == 10
    assert p5.get_option_by_name("other") == 5

    # map_to_cli with l/t present manually (to bypass map_from_cli in __init__)
    p_cli_manual = Profile()
    p_cli_manual.add_backend_option("l", 1)
    p_cli_manual.add_backend_option("t", 2)
    p_cli_manual.add_backend_option("br-x", 11)
    p_cli_manual.add_backend_option("br-y", 12)
    p5_manual = p_cli_manual.map_to_cli(options)
    assert p5_manual.get_option_by_name("x") == 10
    assert p5_manual.get_option_by_name("y") == 10

    # map_to_cli without any tl-x/l/tl-y/t
    p_no_coords = Profile(backend=[("br-x", 11), ("br-y", 12)])
    p5_no_coords = p_no_coords.map_to_cli(options)
    assert p5_no_coords.get_option_by_name("x") == 11
    assert p5_no_coords.get_option_by_name("y") == 12


def test_map_to_cli_variants():
    "test map_to_cli boolean and None options"
    p6 = Profile(backend=[("bool-opt", True)])
    options = unittest.mock.Mock()
    options.by_name.return_value = {"type": enums.TYPE_BOOL}
    p7 = p6.map_to_cli(options)
    assert p7.get_option_by_name("bool-opt") == "yes"

    p6 = Profile(backend=[("bool-opt", False)])
    p7 = p6.map_to_cli(options)
    assert p7.get_option_by_name("bool-opt") == "no"

    # map_to_cli with None options
    p4 = Profile(backend=[("tl-x", 1)])
    p8 = p4.map_to_cli(None)
    assert p8.get_option_by_name("l") == 1
