"""Test writing image."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

from PIL import Image

from scantpaper import config
from scantpaper.document import Document
from scantpaper.loop_helpers import safe_mainloop

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import SimpleNamespace


def test_save_image(
    rose_pnm: str,
    temp_db: SimpleNamespace,
    temp_jpg: object,
    temp_png: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing image."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    mlp = safe_mainloop(2000)
    slist.save_image(
        path=temp_jpg.name,
        list_of_pages=[slist.data[0][2]],
        options={
            "post_save_hook": f"{config.CONVERT_COMMAND} %i {temp_png.name}",
        },
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    img = Image.open(temp_jpg.name)
    assert img.format == "JPEG", "valid JPG created"
    assert img.size == (70, 46), "valid JPG dimensions"

    img = Image.open(temp_png.name)
    assert img.format == "PNG", "ran post-save hook"
    assert img.size == (70, 46), "post-save hook dimensions"


def test_save_image_with_quote(
    rose_pnm: str,
    temp_db: SimpleNamespace,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """Test writing image."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_pnm])
    with tempfile.NamedTemporaryFile(prefix="'", suffix=".jpg") as temp_jpg:
        mlp = safe_mainloop(2000)
        slist.save_image(
            path=temp_jpg.name,
            list_of_pages=[slist.data[0][2]],
            finished_callback=lambda _response: mlp.quit(),
        )
        mlp.run()

        img = Image.open(temp_jpg.name)
        assert img.format == "JPEG", "valid JPG created"
        assert img.size == (70, 46), "valid JPG dimensions"


def test_save_image_with_ampersand(
    rose_pnm: str,
    temp_db: SimpleNamespace,
    import_in_mainloop: Callable[[object, list[str]], None],
    clean_up_files: Callable[[list[str]], None],
) -> None:
    """Test writing image."""
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm])

    path = "sed & awk.png"

    mlp = safe_mainloop(2000)
    slist.save_image(
        path=path,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    img = Image.open(path)
    assert img.format == "PNG", "valid PNG created"
    assert img.size == (70, 46), "valid PNG dimensions"

    #########################

    clean_up_files([path])
