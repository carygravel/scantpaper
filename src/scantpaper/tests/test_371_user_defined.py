"""Test user-defined tools."""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Any, cast

from scantpaper import config
from scantpaper.const import A4_HEIGHT_MM, A4_WIDTH_MM, MM_PER_INCH
from scantpaper.document import Document
from scantpaper.loop_helpers import safe_mainloop

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.basethread import Response


def test_udt(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test user-defined tools."""
    paper_sizes: dict[str, object] = {
        "A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }

    subprocess.run(
        [config.CONVERT_COMMAND, "-size", "210x297", "xc:white", temp_pnm.name],
        check=True,
    )

    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pnm.name])

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == MM_PER_INCH, "Resolution of imported image"

    set_text_in_mainloop(
        slist,
        cast("str", cast("object", 1)),
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]',
    )

    mlp = safe_mainloop(5000)
    slist.user_defined(
        page=slist.data[0][2],
        command="convert %i -negate %o",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(5000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.mean == [0.0], "User-defined with %i and %o"
    assert page.resolution[0] == MM_PER_INCH, "Resolution of converted image"
    assert re.search("ACCOUNT", page.text_layer), "OCR output still there"
    assert not page.saved, "modification removed saved tag"
    assert not slist.thread.pages_saved(), "modification removed saved tag"


def test_udt_in_place(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test user-defined tools."""
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    mlp = safe_mainloop(5000)
    slist.user_defined(
        page=slist.data[0][2],
        command="convert %i -negate %i",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(5000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.mean == [0.0], "User-defined with %i"


def test_udt_page_size(
    temp_pnm: object,
    temp_pdf: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test user-defined tools."""
    paper_sizes: dict[str, object] = {
        "A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }

    subprocess.run(
        [config.CONVERT_COMMAND, "-size", "210x297", "xc:white", temp_pnm.name],
        check=True,
    )

    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)

    import_in_mainloop(slist, [temp_pnm.name])

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == MM_PER_INCH, "Resolution of imported image"

    mlp = safe_mainloop(5000)
    slist.user_defined(
        page=slist.data[0][2],
        command="convert %i tmp.pbm;mv tmp.pbm %i",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution[0] == MM_PER_INCH, "Resolution of image after udt"

    mlp = safe_mainloop(5000)
    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    new = subprocess.check_output(
        ["pdfinfo", temp_pdf.name],
        text=True,
    )
    assert re.search("A4", new), "PDF is A4"


def test_udt_resolution(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_resolution_in_mainloop: Callable[[object, str, float, float], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test user-defined tools."""
    subprocess.run(
        [config.CONVERT_COMMAND, "-size", "210x297", "xc:white", temp_pnm.name],
        check=True,
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])
    set_resolution_in_mainloop(slist, cast("str", cast("object", 1)), 10, 10)

    mlp = safe_mainloop(5000)
    slist.user_defined(
        page=slist.data[0][2],
        command="convert %i tmp.ppm;mv tmp.ppm %i",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.resolution == (
        10,
        10,
        "PixelsPerInch",
    ), "Resolution of converted image taken from input"


def test_udt_error(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test user-defined tools."""
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_pnm.name])

    asserts = 0

    def logger_cb(response: Response) -> None:
        nonlocal asserts
        assert re.search(r"error", cast("dict[str, Any]", response.info)["info"]), (
            "error_cb"
        )
        asserts += 1

    mlp = safe_mainloop(5000)
    slist.user_defined(
        page=slist.data[0][2],
        command="echo error > /dev/stderr;convert %i -negate %i",
        logger_callback=logger_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(5000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = get_page_sync(slist.thread, id=1)
    assert page.mean == [0.0], "User-defined after error"


def test_udt_batch(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test running a user-defined tool over several pages at once."""
    paper_sizes: dict[str, object] = {
        "A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "l": 0, "t": 0},
        "US Letter": {"x": 216, "y": 279, "l": 0, "t": 0},
        "US Legal": {"x": 216, "y": 356, "l": 0, "t": 0},
    }
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)
    slist.set_paper_sizes(paper_sizes)
    import_in_mainloop(slist, [temp_pnm.name, temp_pnm.name])
    set_text_in_mainloop(slist, cast("str", cast("object", 1)), "[{'page':1}]")
    orig_res = get_page_sync(slist.thread, id=1).resolution[0]

    mlp = safe_mainloop(5000)
    slist.user_defined(
        pages=[cast("int", slist.data[0][2]), cast("int", slist.data[1][2])],
        command="mogrify -negate %i",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(5000)
    slist.analyse(
        list_of_pages=[slist.data[0][2], slist.data[1][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    for page_id in (1, 2):
        page = get_page_sync(slist.thread, id=page_id)
        assert page.mean == [0.0], "batch user-defined negated both pages"
        assert page.resolution[0] == orig_res, "resolution preserved in batch"
        assert not page.saved, "batch modification removed saved tag"
    assert not slist.thread.pages_saved(), "batch modification removed saved tag"
    page = get_page_sync(slist.thread, id=1)
    assert re.search("page", page.text_layer), "text layer preserved in batch"


def test_udt_batch_rejects_per_page_only(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test that batch mode refuses a tool using %o or %r."""
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pnm.name])

    assert_with_errors: list[str] = []

    def error_cb(response: Response) -> None:
        assert_with_errors.append(cast("str", response.info))
        mlp.quit()

    for command in ("convert %i %o", "convert %i %r"):
        mlp = safe_mainloop(5000)
        slist.user_defined(
            pages=[cast("int", slist.data[0][2])],
            command=command,
            error_callback=error_cb,
        )
        mlp.run()

    assert len(assert_with_errors) == 2, "one error per refused batch"
    assert all("Batch" in msg for msg in assert_with_errors), "errors name batch mode"


def test_udt_batch_no_changes(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test that a batch leaving every page unchanged reports a message."""
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pnm.name])

    messages: list[str] = []

    def message_cb(response: Response) -> None:
        info = response.info
        if isinstance(info, dict):
            messages.append(cast("str", info["info"]))

    mlp = safe_mainloop(5000)
    slist.user_defined(
        pages=[cast("int", slist.data[0][2])],
        command="echo nothing",
        message_callback=message_cb,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    assert len(messages) == 1, "no-changes message emitted"
    assert "No pages were modified" in messages[0]


def test_udt_batch_undo(
    temp_pnm: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test that a batch forms a single undo step."""
    subprocess.run([config.CONVERT_COMMAND, "xc:white", temp_pnm.name], check=True)

    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_pnm.name, temp_pnm.name])

    def luma(page_id: int) -> int:
        page = get_page_sync(slist.thread, id=page_id)
        return cast("int", page.image_object.convert("L").getpixel((0, 0)))

    pages = [cast("int", slist.data[0][2]), cast("int", slist.data[1][2])]
    mlp = safe_mainloop(5000)
    slist.begin_undo_batch()
    slist.user_defined(
        pages=pages,
        command="mogrify -negate %i",
        finished_callback=lambda _response: mlp.quit(),
    )
    slist.end_undo_batch()
    mlp.run()

    assert luma(1) == 0, "batch negated both pages"
    assert luma(2) == 0, "batch negated both pages"

    mlp = safe_mainloop(5000)
    slist.undo(finished_callback=mlp.quit)
    mlp.run()

    assert luma(1) == 255, "single undo restores both pages"
    assert luma(2) == 255, "single undo restores both pages"

    mlp = safe_mainloop(5000)
    slist.unundo(finished_callback=mlp.quit)
    mlp.run()

    assert luma(1) == 0, "single redo re-applies both pages"
    assert luma(2) == 0, "single redo re-applies both pages"
