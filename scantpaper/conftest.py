"Some helper functions to reduce boilerplate"

import pytest
from gi.repository import GLib


@pytest.fixture
def import_in_mainloop():
    "import paths in a blocking mainloop"

    def anonymous(slist, paths):
        mlp = GLib.MainLoop()
        slist.import_files(paths=paths, finished_callback=mlp.quit)
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

    return anonymous
