"Test importing scan"

from pathlib import Path
import subprocess
import tempfile
import pytest
from gi.repository import GLib
from document import Document
from dialog import Dialog
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # pylint: disable=wrong-import-position


def test_1(clean_up_files):
    "Test importing scan"
    pytest.skip("This has got to wait for test_06* to be finished")
    window = Gtk.Window()
    dialog = Dialog(title="title", transient_for=window)
    slist = Document()

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])
