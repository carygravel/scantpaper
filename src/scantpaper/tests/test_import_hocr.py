"""End-to-end test for rebuilding a session and importing its hOCR."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, cast

from PIL import Image

from scantpaper.document import Document
from scantpaper.loop_helpers import safe_mainloop

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable

    from scantpaper.page import Page


def test_rebuild_session_and_import_hocr(
    tmp_path: pathlib.Path,
    import_in_mainloop: Callable[[object, list[str]], None],
    set_text_in_mainloop: Callable[[object, str, str], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Export text, rebuild the session from images, and import the text."""
    image_path = tmp_path / "page.png"
    Image.new("L", (200, 120), 255).save(image_path)

    old = Document(db=str(tmp_path / "old.sdb"))
    import_in_mainloop(old, [str(image_path), str(image_path)])
    old_ids = [cast("str", row[2]) for row in old.data]
    text_layer = (
        '[{"type": "page", "bbox": [0, 0, 200, 120], "depth": 0}, '
        '{"type": "word", "bbox": [10, 10, 100, 50], '
        '"text": "HELLO", "depth": 1}]'
    )
    set_text_in_mainloop(old, old_ids[0], text_layer)

    hocr_path = tmp_path / "text.hocr"
    mlp = safe_mainloop(2000)
    old.save_hocr(
        path=str(hocr_path),
        list_of_pages=old_ids,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()
    assert hocr_path.read_text(encoding="utf-8").count("class='ocr_page'") == 2, (
        "both pages, including the empty one, are exported"
    )

    new = Document(db=str(tmp_path / "new.sdb"))
    import_in_mainloop(new, [str(image_path), str(image_path)])
    new_ids = [cast("str", row[2]) for row in new.data]
    mlp = safe_mainloop(2000)
    new.import_hocr(
        path=str(hocr_path),
        list_of_pages=new_ids,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    first = cast("Page", get_page_sync(new.thread, id=new_ids[0]))
    second = cast("Page", get_page_sync(new.thread, id=new_ids[1]))
    assert "HELLO" in cast("str", first.text_layer)
    assert second.text_layer is None, "the empty page stays empty"

    pdf_path = tmp_path / "out.pdf"
    mlp = safe_mainloop(5000)
    new.save_pdf(
        path=str(pdf_path),
        list_of_pages=new_ids,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    extracted = subprocess.check_output(["pdftotext", str(pdf_path), "-"], text=True)
    assert "HELLO" in extracted, "imported text is searchable in the PDF"
