"Test saving a djvu with old metadata"

import os
import re
import subprocess
import tempfile
import shutil
import datetime
import pytest
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop):
    "Test saving a djvu with old metadata"

    if shutil.which("cjb2") is None:
        pytest.skip("Please install cjb2 to enable test")

    djvu = "test.djvu"
    pnm = "test.pnm"
    subprocess.run(["convert", "rose:", pnm], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, [pnm])

    called = False

    def error_callback(_result):
        nonlocal called
        called = True

    metadata = {
        "datetime": datetime.datetime(1966, 2, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "title": "metadata title",
    }
    slist.save_djvu(
        path=djvu,
        list_of_pages=[slist.data[0][2].uuid],
        metadata=metadata,
        options={"set_timestamp": True},
        finished_callback=lambda response: mlp.quit(),
        error_callback=error_callback,
    )
    mlp = GLib.MainLoop()
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert called, "caught errors setting timestamp"

    info = subprocess.check_output(["djvused", djvu, "-e", "print-meta"], text=True)
    assert re.search(r"metadata title", info) is not None, "metadata title in DjVu"
    assert re.search(r"1966-02-10", info) is not None, "metadata ModDate in DjVu"

    #########################

    for fname in [pnm, djvu]:
        if os.path.isfile(fname):
            os.remove(fname)
