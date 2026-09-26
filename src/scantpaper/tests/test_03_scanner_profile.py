"""test scanner option profiles."""

from __future__ import annotations

import copy

import pytest

from scantpaper.scanner.profile import Profile, _synonyms


def test_synonyms() -> None:
    """Test synonyms."""
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


def test_profile_basic() -> None:
    """Test basic Profile functionality."""
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


def test_frontend_options() -> None:
    """Test frontend options."""
    profile = Profile()
    profile.add_frontend_option("num_pages", 0)
    assert profile.get() == {
        "backend": [],
        "frontend": {"num_pages": 0},
    }, "basic functionality add_frontend_option"

    itr = profile.each_frontend_option()
    assert next(itr) == "num_pages", "basic functionality each_frontend_option"
    assert profile.get_frontend_option("num_pages") == 0, (
        "basic functionality get_frontend_option"
    )
    with pytest.raises(StopIteration):
        next(itr)

    profile.remove_frontend_option("num_pages")
    assert "num_pages" not in profile.frontend
    profile.remove_frontend_option("non-existent")  # Should not raise


def test_profile_init_data() -> None:
    """Test Profile initialization from data."""
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


def test_profile_init_combined_dict_missing_backend() -> None:
    """Profile from a combined dict with only a frontend key uses empty backend."""
    profile = Profile({"frontend": {"num_pages": 3}})
    assert profile.frontend == {"num_pages": 3}, "frontend extracted"
    assert profile.backend == [], "backend defaults to empty list"


def test_profile_round_trip_legacy_default_scan_options() -> None:
    """A normalised legacy default-scan-options value round-trips via Profile."""
    scan_options: dict[str, object] = {
        "frontend": {},
        "backend": [{"mode": "Binary"}, {"resolution": 600}],
    }
    profile = Profile(scan_options)
    assert profile.get() == {
        "frontend": {},
        "backend": [("mode", "Binary"), ("resolution", 600)],
    }, "legacy default scan options decode to tuples on load"


def test_map_from_cli() -> None:
    """Test map_from_cli."""
    profile = Profile(backend=[("l", 1), ("y", 50), ("x", 50), ("t", 2)])
    assert profile.get() == {
        "backend": [("tl-x", 1), ("br-y", 52), ("br-x", 51), ("tl-y", 2)],
        "frontend": {},
    }, "basic functionality map_from_cli"

    # map_from_cli x/y without l/t
    p3 = Profile(backend=[("x", 10), ("y", 20)])
    assert p3.get_option_by_name("br-x") == 10
    assert p3.get_option_by_name("br-y") == 20


def test_backend_option_iteration() -> None:
    """Test each_backend_option."""
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

    itr = profile.each_backend_option(backwards=True)
    assert next(itr) == 3, "basic functionality each_backend_option reverse"
    for _ in range(1, 4):
        next(itr)
    with pytest.raises(StopIteration):
        next(itr)


def test_remove_backend_option() -> None:
    """Test removal of backend options."""
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


def test_profile_magic_methods() -> None:
    """Test magic methods."""
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


def test_add_backend_option_logic() -> None:
    """Test add_backend_option logic and errors."""
    p1 = Profile()
    # add_backend_option oldval logic
    p1.add_backend_option("opt1", 10, oldval=10)
    assert p1.num_backend_options() == 0

    # add_backend_option error handling
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_backend_option(None, 1)
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_backend_option("", 1)


def test_add_frontend_option_errors() -> None:
    """Test add_frontend_option errors."""
    p1 = Profile()
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_frontend_option(None, 1)
    with pytest.raises(ValueError, match="Error: no option name"):
        p1.add_frontend_option("", 1)
