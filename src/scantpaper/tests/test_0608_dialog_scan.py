"""test scan dialog."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from scantpaper.const import A4_HEIGHT_MM, A4_WIDTH_MM
from scantpaper.frontend import enums
from scantpaper.scanner.options import Option
from scantpaper.scanner.profile import Profile
from scantpaper.tests.scan_mocks import build_scan_options

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from scantpaper.basethread import Request
    from scantpaper.dialog.sane import SaneScanDialog
    from scantpaper.frontend.image_sane import SaneThread
    from scantpaper.loop_helpers import _MainLoopWrapper


def setup_coupled_scan_options(
    mocker: pytest.MockerFixture,
    dlg: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> SaneScanDialog:
    """Patch the SaneThread to alias scan-area and quick-format."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )

    def mocked_do_open_device(self: SaneThread, request: Request) -> None:
        """Open device."""
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            scan_area="Maximum",
            quick_format="Maximum",
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_open_device", mocked_do_open_device
    )

    raw_options = build_scan_options(
        ["resolution-100-200-300-600", "scan-area-maximum-a4"]
    )
    raw_options.append(
        Option(
            index=len(raw_options),
            name="quick-format",
            title="Quick format",
            desc="Quick format",
            type=enums.TYPE_STRING,
            unit=0,
            size=1,
            cap=5,
            constraint=["Maximum", "A4", "A5 Landscape"],
        )
    )

    def mocked_do_get_options(_self: SaneThread, _request: Request) -> list[Option]:
        """mocked_do_get_options."""
        nonlocal raw_options
        return raw_options

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_options", mocked_do_get_options
    )

    def mocked_do_set_option(self: SaneThread, _request: Request) -> int:
        """Revert the other media option when one is set (epkowa GT-20000)."""
        key, value = _request.args
        info = 0
        if key == "scan-area":
            self.device_handle.scan_area = value
            self.device_handle.quick_format = value
            info = enums.INFO_RELOAD_OPTIONS
        elif key == "quick-format":
            self.device_handle.quick_format = value
            self.device_handle.scan_area = value
            info = enums.INFO_RELOAD_OPTIONS
        else:
            setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_set_option", mocked_do_set_option
    )

    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    return dlg


def mocked_do_get_devices(_cls: object, _request: Request) -> list[SimpleNamespace]:
    """mocked_do_get_devices."""
    devices = [("mock_name", "", "", "")]
    return [
        SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1]) for x in devices
    ]


def trigger_get_devices(
    dlg: SaneScanDialog,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Trigger get_devices to cover mocked_do_get_devices."""
    loop = mainloop_with_timeout()

    def reloaded_devices_cb(_arg1: object, _arg2: object) -> None:
        loop.quit()

    handler = dlg.connect("changed-device-list", reloaded_devices_cb)
    dlg.get_devices()
    loop.run()
    dlg.disconnect(handler)


def test_infinite_reloads(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
    infinite_reloads_scan_mocks: SimpleNamespace,
) -> None:
    """Test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )
    infinite_reloads_scan_mocks.patch_open_and_get(mocker)

    def mocked_do_set_option(self: SaneThread, _request: Request) -> int:
        """Force a reload for every option.

        Trigger an infinite reload loop and test that the reload-recursion-limit
        is respected.
        """
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_set_option", mocked_do_set_option
    )

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_sizes = {"A4": {"x": A4_WIDTH_MM, "y": A4_HEIGHT_MM, "t": 0, "l": 0}}

    def changed_paper_cb(_arg1: object, _arg2: object) -> None:
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
    assert dlg.num_reloads < 6, "finished reload loops without recursion limit"
    assert dlg.current_scan_options.get_option_by_name("resolution") == 100, (
        "profile option converged without being dropped"
    )
    assert dlg.current_scan_options.get_option_by_name("source") == "Flatbed", (
        "second profile option converged without being dropped"
    )


def test_coupled_scan_options_drop_reverted(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Coupled media options give up per-option instead of hitting the limit.

    Reproduces the epkowa GT-20000 case from the log files: scan-area and
    quick-format are aliased in the backend, so setting one reverts the
    other. The apply must drop the reverted option after K re-applies, keep
    the healthy options, and finish without the reload-recursion-limit error.
    """
    dlg = setup_coupled_scan_options(
        mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
    )
    loop = mainloop_with_timeout()

    def settled_with_drop() -> bool:
        return (
            not dlg.setting_current_scan_options
            and dlg.current_scan_options.get_option_by_name("scan-area") is None
            and dlg.current_scan_options.get_option_by_name("quick-format") is not None
        )

    def changed_current_scan_options_cb(
        _widget: object, _profile: object, _uuid: object
    ) -> None:
        if settled_with_drop():
            dlg.disconnect(signal)
            loop.quit()

    signal = dlg.connect(
        "changed-current-scan-options", changed_current_scan_options_cb
    )
    dlg.set_current_scan_options(
        Profile(
            backend=[
                ("resolution", 100),
                ("scan-area", "A5 Landscape"),
                ("quick-format", "A4"),
            ]
        )
    )

    loop.run()

    assert dlg.current_scan_options.get_option_by_name("scan-area") is None, (
        "reverted option dropped"
    )
    assert dlg.current_scan_options.get_option_by_name("quick-format") == "A4", (
        "non-reverted option kept"
    )
    assert dlg.current_scan_options.get_option_by_name("resolution") == 100, (
        "healthy option still applied"
    )
    assert dlg._reverted_option_counts["scan-area"] == 2, "set at most K=2 times"
    assert [n for n, _v in dlg.current_scan_options.get()["backend"]] == [
        "resolution",
        "quick-format",
    ], "dropped option is not persisted in current scan options"
    assert dlg.num_reloads < dlg.reload_recursion_limit, "no recursion limit hit"


def test_apply_after_drop_starts_fresh(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """A second apply is not harmed by a previous one that dropped an option."""
    dlg = setup_coupled_scan_options(
        mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
    )

    def apply_profile(profile: Profile, condition: Callable[[], bool]) -> None:
        loop = mainloop_with_timeout()
        signal = None

        def changed_current_scan_options_cb(
            _widget: object, _profile: object, _uuid: object
        ) -> None:
            if condition():
                dlg.disconnect(signal)
                loop.quit()

        signal = dlg.connect(
            "changed-current-scan-options", changed_current_scan_options_cb
        )
        dlg.set_current_scan_options(profile)
        loop.run()

    apply_profile(
        Profile(
            backend=[
                ("resolution", 100),
                ("scan-area", "A5 Landscape"),
                ("quick-format", "A4"),
            ]
        ),
        lambda: (
            not dlg.setting_current_scan_options
            and dlg.current_scan_options.get_option_by_name("scan-area") is None
        ),
    )
    assert dlg.current_scan_options.get_option_by_name("scan-area") is None, (
        "first apply dropped the reverted option"
    )

    apply_profile(
        Profile(backend=[("scan-area", "A4")]),
        lambda: (
            not dlg.setting_current_scan_options
            and dlg.current_scan_options.get_option_by_name("scan-area") == "A4"
        ),
    )
    assert dlg.current_scan_options.get_option_by_name("scan-area") == "A4", (
        "second apply was not affected by the earlier drop"
    )
    assert dlg._reverted_option_counts["scan-area"] == 1, (
        "counters reset at the start of each apply"
    )


def test_linear_reload_backstop(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
    infinite_reloads_scan_mocks: SimpleNamespace,
) -> None:
    """The reload budget is linear in the option count, not triangular."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )
    infinite_reloads_scan_mocks.patch_open_and_get(mocker)
    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")

    num = dlg.available_scan_options.num_options()
    assert dlg.reload_recursion_limit == 3 * num, "linear reload budget"
    assert dlg.reload_recursion_limit < num * (num + 1) // 2, (
        "smaller than the old triangular budget"
    )


def test_changed_profile(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
    infinite_reloads_scan_mocks: SimpleNamespace,
) -> None:
    """Test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )
    infinite_reloads_scan_mocks.patch_open_and_get(mocker)

    def mocked_do_set_option(self: SaneThread, _request: Request) -> int:
        """Guard against the changed-profile signal being emitted too early.

        This resulted in the profile dropdown being set to None.
        """
        key, value = _request.args
        setattr(self.device_handle, key.replace("-", "_"), value)
        return enums.INFO_RELOAD_OPTIONS

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_set_option", mocked_do_set_option
    )

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    dlg._add_profile(
        "my profile", Profile(backend=[("resolution", 100), ("source", "Flatbed")])
    )
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    asserts = 0

    def changed_profile_cb(_widget: object, profile: object) -> None:
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert profile == "my profile", "changed-profile"
        assert dlg.current_scan_options == Profile(
            backend=[("resolution", 100), ("source", "Flatbed")],
        ), "current-scan-options with profile"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"

    loop.run()

    assert asserts == 1, "all callbacks ran"


def test_source_default(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )

    def mocked_do_open_device(self: SaneThread, request: Request) -> None:
        """Open device."""
        device_name = request.args[0]
        self.device_handle = SimpleNamespace()
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_open_device", mocked_do_open_device
    )

    def mocked_do_get_options(_self: SaneThread, _request: Request) -> list[Option]:
        """Reproduce an Acer flatbed scanner using a snapscan backend with no source default.

        As the source only had one possibility, which was never set, the source
        option never had a value. Check that the number of pages frame is ghosted.
        """
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
                name="source",
                title="Scan source",
                desc="Selects the scan source (such as a document-feeder).",
                type=3,
                unit=0,
                size=1,
                cap=53,
                constraint=["Flatbed"],
            ),
        ]

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_options", mocked_do_get_options
    )

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    mainloop_with_timeout()

    options = dlg.available_scan_options
    assert options.flatbed_selected(dlg.thread.get_option_value), (
        "flatbed_selected() without value"
    )
    assert not dlg.framen.is_sensitive(), "num-page gui ghosted"
    dlg.num_pages = 2
    assert dlg.num_pages == 1, "allow-batch-flatbed should force num-pages"
    dlg.allow_batch_flatbed = True
    dlg.num_pages = 2
    assert dlg.num_pages == 2, "num-pages"
    assert dlg.framen.is_sensitive(), "num-page gui not ghosted"


def test_more_profiles(
    sane_scan_dialog: SaneScanDialog,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Check options are reset before applying a profile."""
    dlg = sane_scan_dialog
    dlg._add_profile("my profile", Profile(backend=[("resolution", 100)]))
    loop = mainloop_with_timeout()
    asserts = 0

    def reloaded_scan_options_cb(_arg: object) -> None:
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("reloaded-scan-options", reloaded_scan_options_cb)
    dlg.device = "test"
    dlg.scan_options()
    loop.run()

    loop = mainloop_with_timeout()

    def changed_scan_option_cb(
        _arg: object, _arg2: object, _arg3: object, _arg4: object
    ) -> None:
        dlg.disconnect(dlg.signal)
        loop.quit()

    dlg.signal = dlg.connect("changed-scan-option", changed_scan_option_cb)
    dlg.set_option(dlg.available_scan_options.by_name("tl-x"), 10)
    loop.run()

    loop = mainloop_with_timeout()

    def changed_profile_cb(_widget: object, _profile: object) -> None:
        nonlocal asserts
        dlg.disconnect(dlg.signal)
        assert dlg.current_scan_options == Profile(backend=[("resolution", 100)]), (
            "reset before applying profile"
        )
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-profile", changed_profile_cb)
    dlg.profile = "my profile"
    loop.run()

    assert asserts == 1, "all callbacks ran"
    dlg.thread.quit()


def test_button_press(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Test more of scan dialog by mocking do_get_devices(), do_open_device() & do_get_options()."""
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )

    def mocked_do_open_device(self: SaneThread, request: Request) -> None:
        """Open device."""
        device_name = request.args[0]
        self.device_handle = SimpleNamespace(
            resolution=75,
            tl_x=0,
            tl_y=0,
            br_x=216.699996948242,
            br_y=300.0,
            clear_calibration=None,
        )
        self.device = device_name
        request.data(f"opened device '{self.device_name}'")

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_open_device", mocked_do_open_device
    )

    raw_options = build_scan_options(
        [
            "resolution-100-200-300-600",
            "tl-x-215900",
            "tl-y-297010",
            "br-x-215900",
            "br-y-297010",
            "clear-calibration",
        ]
    )

    def mocked_do_get_options(_self: SaneThread, _request: Request) -> list[Option]:
        """mocked_do_get_options."""
        nonlocal raw_options
        return raw_options

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_options", mocked_do_get_options
    )

    def mocked_do_set_option(self: SaneThread, _request: Request) -> int:
        """Reload clear-calibration button pressed.

        Test that this doesn't trigger an infinite reload loop.
        """
        key, value = _request.args
        for opt in raw_options:
            if opt.name == key:
                break
        info = 0
        if key == "clear-calibration":
            info = enums.INFO_RELOAD_OPTIONS
        else:
            setattr(self.device_handle, key.replace("-", "_"), value)
        return info

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_set_option", mocked_do_set_option
    )

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")
    loop = mainloop_with_timeout()
    dlg.paper_sizes = {"A4": {"x": 210, "y": 279, "t": 0, "l": 0}}
    asserts = 0

    def changed_paper_cb(_arg1: object, _arg2: object) -> None:
        dlg.disconnect(dlg.signal)
        nonlocal asserts
        assert dlg.current_scan_options == Profile(
            backend=[
                ("resolution", 100),
                ("clear-calibration", None),
                ("br-x", 210.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "A4"},
        ), "all options applied"
        asserts += 1
        loop.quit()

    dlg.signal = dlg.connect("changed-paper", changed_paper_cb)
    dlg.set_current_scan_options(
        Profile(
            backend=[
                ("resolution", 100),
                ("clear-calibration", None),
                ("br-x", 210.0),
                ("br-y", 279.0),
            ],
            frontend={"paper": "A4"},
        )
    )

    loop.run()
    assert dlg.num_reloads < 6, "finished reload loops without recursion limit"
    assert asserts == 1, "ran all callbacks"


def test_get_invalid_option(
    mocker: pytest.MockerFixture,
    sane_scan_dialog: SaneScanDialog,
    set_device_wait_reload: Callable[[SaneScanDialog, str], None],
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Test getting an invalid option (gscan2pdf bug #313).

    scanimage was segfaulting when retrieving the options from a Brother
    ADS-2800W via --help. xsane and simplescan worked.

    gscan2pdf tested this with 06092_dialog_scan, but without a load of
    debugging help from someone with access to a similar scanner, it is
    hard to predict how the python sane module would react.
    """
    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices
    )

    def mocked_do_open_device(self: SaneThread, request: Request) -> None:
        """Open device."""
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

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_open_device", mocked_do_open_device
    )

    raw_options = build_scan_options(
        [
            "resolution-100-200-300-600",
            "source-flatbed-adf",
            "tl-x-215900",
            "tl-y-297010",
            "br-x-215900",
            "br-y-297010",
            "select-detect",
        ]
    )

    def mocked_do_get_options(_self: SaneThread, _request: Request) -> list[Option]:
        """mocked_do_get_options."""
        nonlocal raw_options
        return raw_options

    mocker.patch(
        "scantpaper.dialog.sane.SaneThread.do_get_options", mocked_do_get_options
    )

    dlg = sane_scan_dialog
    trigger_get_devices(dlg, mainloop_with_timeout)
    set_device_wait_reload(dlg, "mock_name")

    assert dlg.available_scan_options.by_index(7) == Option(
        cap=0,
        name=None,  # "select-detect"
        title=None,
        desc=None,
        constraint=None,
        size=1,
        type=enums.TYPE_BOOL,
        unit=None,
        index=7,
    ), "make options that throw an error undetectable and unselectable"
