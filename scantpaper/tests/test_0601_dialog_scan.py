"test scan dialog"

import os
import glob
import subprocess
import tempfile
from types import SimpleNamespace
import gi
from document import Document
from dialog.scan import Scan
from frontend import enums
from scanner.options import Option
from scanner.profile import Profile

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # pylint: disable=wrong-import-position


def test_basics():
    "test basic functionality of scan dialog"

    window = Gtk.Window()

    dialog = Scan(
        title="title",
        transient_for=window,
    )
    assert isinstance(dialog, Scan), "Created dialog"

    dialog.sided = "double"
    dialog.side_to_scan = "reverse"

    # After having scanned some double-sided pages on a simplex scanner,
    # selecting single-sided again should also select facing page.
    dialog.sided = "single"
    assert dialog.side_to_scan == "facing", "selecting single sided also selects facing"

    dialog.checkx.set_active(True)
    dialog.page_number_increment = 3
    dialog.checkx.set_active(False)
    assert (
        dialog.page_number_increment == 2
    ), "turning off extended page numbering resets increment"

    assert dialog.allow_batch_flatbed == 0, "default allow-batch-flatbed"
    dialog.allow_batch_flatbed = True
    dialog.num_pages = 2
    assert dialog.num_pages == 2, "num-pages"
    assert dialog.framen.is_sensitive(), "num-page gui not ghosted"
    dialog.allow_batch_flatbed = False
    assert (
        dialog.num_pages == 2
    ), "with no source, num-pages not affected by allow-batch-flatbed"
    assert dialog.framen.is_sensitive(), "with no source, num-page gui not ghosted"


def test_doc_interaction(clean_up_files):
    "test interaction of scan dialog and document"

    window = Gtk.Window()

    dialog = Scan(
        title="title",
        transient_for=window,
    )
    slist = Document()
    dialog = Scan(
        title="title",
        transient_for=window,
        document=slist,
    )
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    with tempfile.TemporaryDirectory() as tempdir:
        options = {
            "filename": "test.pnm",
            "resolution": (72, 72, "PixelsPerInch"),
            "page": 1,
            "dir": tempdir,
        }
        slist.import_scan(**options)
        options["page"] = 2
        slist.import_scan(**options)
        options["page"] = 4
        slist.import_scan(**options)
        options["page"] = 5

        asserts = 0
        mlp = GLib.MainLoop()

        def finished_callback(_response):
            nonlocal asserts
            assert (
                dialog.page_number_start == 3
            ), "adding pages should update page-number-start"
            assert dialog.num_pages == 1, "adding pages should update num-pages"
            asserts += 1
            mlp.quit()

        options["finished_callback"] = finished_callback
        slist.import_scan(**options)
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()
        assert asserts == 1, "ran finished callback"

        # v2.6.3 had the bug where scanning 10 pages on single-sided, followed by
        # 10 pages double-sided reverse resulted in the reverse pages being numbered:
        # 11, 9, 7, 5, 3, 1, -1, -3, -5, -7
        dialog.allow_batch_flatbed = True
        slist.data = [[1, None, None], [3, None, None], [5, None, None]]
        dialog.page_number_start = 6
        dialog.num_pages = 0
        dialog.side_to_scan = "reverse"
        assert (
            dialog.num_pages == 3
        ), "selecting reverse should automatically limit the number of pages to scan"
        assert (
            dialog.max_pages == 3
        ), "selecting reverse should automatically limit the max number of pages to scan"

        clean_up_files(["test.pnm"] + glob.glob(f"{tempdir}/*"))
        os.rmdir(tempdir)


def test_profiles(sane_scan_dialog, mainloop_with_timeout, set_option_in_mainloop):
    "first test with test backend"

    dialog = sane_scan_dialog
    dialog.paper_formats = {
        "new": {
            "l": 0.0,
            "y": 10.0,
            "x": 10.0,
            "t": 0.0,
        }
    }

    dialog.num_pages = 2

    asserts = 0

    def reloaded_scan_options_cb(_dialog):
        nonlocal signal
        nonlocal asserts
        nonlocal loop
        dialog.disconnect(signal)
        loop.quit()

    dialog.device = "test"
    dialog.scan_options()
    loop = mainloop_with_timeout()
    signal = dialog.connect("reloaded-scan-options", reloaded_scan_options_cb)
    loop.run()

    options = dialog.available_scan_options

    # Check that profiles are being saved properly,
    assert set_option_in_mainloop(dialog, "tl-x", 10)
    assert set_option_in_mainloop(dialog, "tl-y", 10)
    dialog.save_current_profile("profile 1")
    assert dialog.profiles["profile 1"] == Profile(
        backend=[
            ("tl-x", 10),
            ("tl-y", 10),
        ],
    ), "applied 1st profile"
    assert dialog.profile == "profile 1", "saving current profile sets profile"

    assert set_option_in_mainloop(dialog, "tl-x", 20)
    assert set_option_in_mainloop(dialog, "tl-y", 20)
    dialog.save_current_profile("profile 2")
    assert dialog.profiles["profile 2"] == Profile(
        backend=[("tl-x", 20), ("tl-y", 20)]
    ), "applied 2nd profile"
    assert dialog.profiles["profile 1"] == Profile(
        backend=[
            ("tl-x", 10),
            ("tl-y", 10),
        ],
    ), "applied 2nd profile without affecting 1st"
    dialog._remove_profile("profile 1")
    assert dialog.profiles["profile 2"] == Profile(
        backend=[("tl-x", 20), ("tl-y", 20)]
    ), "remove_profile()"
    assert dialog.thread.device_handle.source == "Flatbed", "source defaults to Flatbed"
    assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages"
    assert not dialog.framen.is_sensitive(), "num-page gui ghosted"
    dialog.num_pages = 2
    assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages2"
    assert options.flatbed_selected(
        dialog.thread.device_handle
    ), "flatbed_selected() via value"
    assert not dialog._vboxx.get_visible(), "flatbed, so hide vbox for page numbering"

    asserts = asserts_2(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts)
    asserts_3(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts)


def asserts_2(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts):
    "splitting test_1 up into chunks"
    options = dialog.available_scan_options

    dialog.allow_batch_flatbed = True
    dialog.num_pages = 2

    def changed_num_pages_cb(self, _data):
        nonlocal asserts
        nonlocal signal
        dialog.disconnect(signal)
        assert dialog.num_pages == 1, "allow-batch-flatbed should force num-pages3"
        assert not dialog.framen.is_sensitive(), "num-page gui ghosted2"
        asserts += 1

    signal = dialog.connect("changed-num-pages", changed_num_pages_cb)
    dialog.allow_batch_flatbed = False
    loop = mainloop_with_timeout()
    assert (
        dialog.adf_defaults_scan_all_pages == 1
    ), "default adf-defaults-scan-all-pages"

    def changed_scan_option_cb(widget, option, value, _data):

        if option == "source":
            nonlocal asserts
            nonlocal signal
            dialog.disconnect(signal)
            assert (
                dialog.num_pages == 0
            ), "adf-defaults-scan-all-pages should force num-pages"
            assert not options.flatbed_selected(
                dialog.thread.device_handle
            ), "not flatbed_selected() via value"
            asserts += 1
            loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb)
    dialog.set_option(options.by_name("source"), "Automatic Document Feeder")
    loop.run()

    assert set_option_in_mainloop(dialog, "source", "Flatbed")
    dialog.num_pages = 1

    loop = mainloop_with_timeout()

    def changed_scan_option_cb3(_widget, _option, _value, _data):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        assert False, "should not try to set invalid option"
        loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb3)

    def changed_current_scan_options_cb(_arg1, _arg2, _arg3):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        loop.quit()

    signal2 = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    dialog.set_current_scan_options(Profile(backend=[("mode", "Lineart")]))
    loop.run()
    return asserts


def asserts_3(mainloop_with_timeout, set_option_in_mainloop, dialog, asserts):
    "splitting test_1 up into chunks"
    loop = mainloop_with_timeout()

    def changed_scan_option_cb4(_widget, _option, _value, _data):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        assert False, "should not try to set option if value already correct"
        loop.quit()

    signal = dialog.connect("changed-scan-option", changed_scan_option_cb4)

    def changed_current_scan_options_cb2(_arg1, _arg2, _arg3):
        nonlocal signal
        nonlocal signal2
        dialog.disconnect(signal)
        dialog.disconnect(signal2)
        loop.quit()

    signal2 = dialog.connect(
        "changed-current-scan-options", changed_current_scan_options_cb2
    )

    def add_mode_gray_cb():
        dialog.set_current_scan_options(Profile(backend=[("mode", "Gray")]))

    GLib.idle_add(add_mode_gray_cb)
    loop.run()

    dialog.adf_defaults_scan_all_pages = 0
    assert set_option_in_mainloop(dialog, "source", "Automatic Document Feeder")
    assert dialog.num_pages == 1, "adf-defaults-scan-all-pages should force num-pages 2"
    assert dialog._vboxx.get_visible(), "simplex ADF, so show vbox for page numbering"

    # bug in 2.5.3 where setting paper via default options only
    # set combobox without setting options
    loop = mainloop_with_timeout()

    def changed_paper_cb(_arg1, _arg2):
        nonlocal asserts
        nonlocal signal
        dialog.disconnect(signal)
        assert dialog.current_scan_options == Profile(
            frontend={"paper": "new"},
            backend=[
                ("tl-x", 0.0),
                ("tl-y", 0.0),
                ("br-x", 10.0),
                ("br-y", 10.0),
            ],
        ), "set paper with conflicting options"
        asserts += 1
        loop.quit()

    signal = dialog.connect("changed-paper", changed_paper_cb)
    dialog.set_current_scan_options(
        Profile(
            backend=[
                ("tl-x", 20.0),
                ("tl-y", 20.0),
            ],
            frontend={"paper": "new"},
        )
    )
    loop.run()

    # bug previous to v2.1.7 where having having set double sided and
    # reverse, and then switched from ADF to flatbed, clicking scan produced
    # the error message that the facing pages should be scanned first
    dialog.side_to_scan = "reverse"
    assert set_option_in_mainloop(dialog, "source", "Flatbed")
    assert dialog.sided == "single", "selecting flatbed forces single sided"
    assert set_option_in_mainloop(dialog, "br-y", 9.0)
    loop = mainloop_with_timeout()
    dialog.connect("changed-paper", lambda x, y: loop.quit)
    dialog.paper = None
    loop.run()
    assert dialog.current_scan_options == Profile(
        backend=[
            ("tl-x", 0.0),
            ("tl-y", 0.0),
            ("br-x", 10.0),
            ("source", "Flatbed"),
            ("br-y", 9.0),
        ],
    ), "set Manual paper"
    assert (
        dialog.combobp.get_num_rows() == 3
    ), "available paper reapplied after setting/changing device"
    assert dialog.combobp.get_active_text() == "Manual", "paper combobox has a value"
    assert asserts == 3, "call callbacks run"
    dialog.thread.quit()


def test_scan_threads(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(self, _request):
        """Options with opt.type == SANE_TYPE_GROUP don't necessarily then have
        opt.name defined, which was triggering an error
        when reloading the options. Override enough to test for this."""
        nonlocal asserts
        asserts += 1
        self.device_handle.source = "Auto"
        return [
            Option(
                index=0,
                name="",
                title="Number of options",
                desc="Read-only option that specifies how many options a specific device supports.",
                type=1,
                unit=0,
                size=4,
                cap=4,
                constraint=None,
            ),
            Option(
                index=1,
                name="",
                title="Scan mode",
                desc="",
                type=5,
                unit=0,
                size=1,
                cap=0,
                constraint=None,
            ),
            Option(
                index=2,
                name="source",
                title="Scan source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=69,
                constraint=["Auto", "Flatbed", "ADF"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return 0

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

    def changed_scan_option_cb(_widget, _option, _value, _uuid):
        nonlocal asserts
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    options = dlg.available_scan_options
    dlg.set_option(options.by_name("source"), "ADF")

    loop.run()
    assert asserts == 2, "all callbacks runs"


def test_source_without_val(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(self, _request):
        """A Canon Lide 220 was producing scanimage output without a val for source,
        producing the error: Use of uninitialized value in pattern match (m//)
        when loading the options. Override enough to test for this."""
        nonlocal asserts
        asserts += 1
        self.device_handle.source = None
        return [
            Option(
                index=0,
                name="",
                title="Number of options",
                desc="Read-only option that specifies how many options a specific device supports.",
                type=1,
                unit=0,
                size=4,
                cap=4,
                constraint=None,
            ),
            Option(
                index=1,
                name="",
                title="Scan mode",
                desc="",
                type=5,
                unit=0,
                size=1,
                cap=0,
                constraint=None,
            ),
            Option(
                index=2,
                name="source",
                title="Source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=37,
                constraint=["Flatbed", "Transparency Adapter"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return 0

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

    def changed_scan_option_cb(_widget, _option, _value, _uuid):
        nonlocal asserts
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    options = dlg.available_scan_options
    dlg.set_option(options.by_name("source"), "Flatbed")

    loop.run()
    assert asserts == 2, "all callbacks runs"


def test_no_source(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"
    asserts = 0

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    def mocked_do_get_options(self, _request):
        """A Samsung CLX-4190 has a doc-source options instead of source, meaning that
        the property allow-batch-flatbed had to be enabled to scan more than one
        page from the ADF. Override enough to test for this."""
        self.device_handle.doc_source = "Auto"
        return [
            Option(
                index=0,
                name="",
                title="Number of options",
                desc="Read-only option that specifies how many options a specific device supports.",
                type=1,
                unit=0,
                size=4,
                cap=4,
                constraint=None,
            ),
            Option(
                index=1,
                name="doc-source",
                title="Doc source",
                desc="Selects source of the document to be scanned",
                type=3,
                unit=0,
                size=1,
                cap=5,
                constraint=["Auto", "Flatbed", "ADF Simplex"],
            ),
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()

    def changed_current_scan_options_cb(_arg1, _arg2, _arg3):
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert dlg.num_pages == 0, "num-pages"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    dlg.set_current_scan_options(Profile(frontend={"num_pages": 0}))

    loop.run()
    assert asserts == 1, "all callbacks runs"


def test_officejet_4620(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            index=1,
            name="resolution",
            title="Scan resolution",
            desc="Sets the resolution of the scanned image.",
            type=1,
            unit=4,
            size=4,
            cap=5,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        """An Officejet_4620_series was resetting the resolution and geometry when
        changing from ADF to Flatbed. Ensure that valid parts of the current profile
        are still active (updating if necessary) after changing an option that forces
        a reload."""
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(self, _request):
        key, value = _request.args
        info = 0
        if key == "source" and value in "Flatbed":
            raw_options[1] = Option(
                index=1,
                name="resolution",
                title="Scan resolution",
                desc="Sets the resolution of the scanned image.",
                type=1,
                unit=4,
                size=4,
                cap=5,
                constraint=[75, 100, 200, 300, 600, 1200],
            )
            self.device_handle.resolution = 75
            self.device_handle.br_x = 215.900009155273
            info = enums.INFO_RELOAD_OPTIONS

        setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_formats = {"A4": {"x": 210, "y": 297, "t": 0, "l": 0}}

    def changed_paper_cb(_arg1, _arg2):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[("resolution", 100), ("source", "Flatbed")],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.thread.device_handle.resolution == 100, "reset resolution"
    assert dlg.thread.device_handle.br_x == 210, "reset br-x"
    assert dlg.paper == "A4", "reset paper"


def test_infinite_reloads(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()"

    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    def mocked_do_open_device(self, request):
        "open device"
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            source="ADF",
            tl_x=0,
            tl_y=0,
            br_x=215.900009155273,
            br_y=297.010681152344,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            unit=4,
            cap=5,
            index=1,
            desc="Sets the resolution of the scanned image.",
            title="Scan resolution",
            type=1,
            name="resolution",
            size=1,
            constraint=[100, 200, 300, 600],
        ),
        Option(
            type=3,
            size=1,
            name="source",
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=2,
            cap=5,
            unit=0,
        ),
        Option(
            type=2,
            name="tl-x",
            size=1,
            constraint=(0, 215.900009155273, 0),
            title="Top-left x",
            desc="Top-left x position of scan area.",
            index=3,
            cap=5,
            unit=3,
        ),
        Option(
            desc="Top-left y position of scan area.",
            title="Top-left y",
            cap=5,
            index=4,
            name="tl-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            type=2,
            unit=3,
        ),
        Option(
            unit=3,
            size=1,
            name="br-x",
            constraint=(0, 215.900009155273, 0),
            type=2,
            desc="Bottom-right x position of scan area.",
            title="Bottom-right x",
            cap=5,
            index=5,
        ),
        Option(
            type=2,
            name="br-y",
            size=1,
            constraint=(0, 297.010681152344, 0),
            index=6,
            cap=5,
            desc="Bottom-right y position of scan area.",
            title="Bottom-right y",
            unit=3,
        ),
    ]

    def mocked_do_get_options(_self, _request):
        "mocked_do_get_options"
        nonlocal raw_options
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    def mocked_do_set_option(_self, _request):
        """Force a reload for every option to trigger an infinite reload loop and test
        that the reload-recursion-limit is respected."""
        # key, value = _request.args
        # setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch("dialog.sane.SaneThread.do_set_option", mocked_do_set_option)

    dlg = sane_scan_dialog
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_formats = {"A4": {"x": 210, "y": 297, "t": 0, "l": 0}}

    def changed_paper_cb(_arg1, _arg2):
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[("resolution", 100), ("source", "Flatbed")],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.num_reloads > 6, "broke out of reload infinite loop"
