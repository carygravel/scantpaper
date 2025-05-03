"test scanner option profiles"

from scanner.profile import Profile, _synonyms
import pytest


def test_1():
    "test scanner option profiles"
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

    profile = Profile()
    assert isinstance(profile, Profile)
    profile.add_backend_option("y", "297")
    assert profile.get() == {
        "backend": [("y", "297")],
        "frontend": {},
    }, "basic functionality add_backend_option"

    #########################

    profile.add_backend_option("br-y", "297")
    assert profile.get() == {
        "backend": [("br-y", "297")],
        "frontend": {},
    }, "pruned duplicate"

    #########################

    profile.add_frontend_option("num_pages", 0)
    assert profile.get() == {
        "backend": [("br-y", "297")],
        "frontend": {"num_pages": 0},
    }, "basic functionality add_frontend_option"

    #########################

    profile = Profile(frontend={"num_pages": 1}, backend=[("br-x", "297")])
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "basic functionality new_from_data"

    #########################

    profile = Profile({"frontend": {"num_pages": 1}, "backend": [("br-x", "297")]})
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "basic functionality new_from_data with dict"

    #########################

    itr = profile.each_frontend_option()
    assert next(itr) == "num_pages", "basic functionality each_frontend_option"
    assert (
        profile.get_frontend_option("num_pages") == 1
    ), "basic functionality get_frontend_option"
    with pytest.raises(StopIteration):
        next(itr)

    #########################

    profile = Profile(frontend={"num_pages": 1}, backend=[{"br-x": "297"}])
    assert profile.get() == {
        "backend": [("br-x", "297")],
        "frontend": {"num_pages": 1},
    }, "map old pre-v3 profiles to use tuples"

    #########################

    profile = Profile(backend=[("l", 1), ("y", 50), ("x", 50), ("t", 2)])
    assert profile.get() == {
        "backend": [("tl-x", 1), ("br-y", 52), ("br-x", 51), ("tl-y", 2)],
        "frontend": {},
    }, "basic functionality map_from_cli"

    #########################

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

    #########################

    itr = profile.each_backend_option(True)
    assert next(itr) == 3, "basic functionality each_backend_option reverse"
    for _ in range(1, 4):
        next(itr)
    with pytest.raises(StopIteration):
        next(itr)

    #########################

    profile.remove_backend_option_by_name("tl-x")
    assert profile.get() == {
        "backend": [("br-y", 52), ("br-x", 51), ("tl-y", 2)],
        "frontend": {},
    }, "basic functionality remove_backend_option_by_name"
