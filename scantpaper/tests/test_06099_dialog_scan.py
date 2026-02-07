"Tests for dialog.scan.Scan class coverage edge cases."

import logging
from types import SimpleNamespace
import unittest.mock
import pytest
from gi.repository import Gtk, GObject
from dialog.scan import (
    Scan,
    _value_for_active_option,
    make_progress_string,
    _new_val,
    _save_profile_callback,
    _edit_profile_callback,
    do_delete_profile_backend_item,
    _build_profile_table,
)
from frontend import enums
from scanner.options import Option
from scanner.profile import Profile
import gi

gi.require_version("Gtk", "3.0")

logger = logging.getLogger(__name__)


class MockOption:
    "A mock scan option"

    def __init__(
        self, name, otype, unit=enums.UNIT_NONE, cap=0, constraint=None, desc=""
    ):
        self.name = name
        self.title = name
        self.type = otype
        self.unit = unit
        self.cap = cap
        self.constraint = constraint
        self.desc = desc
        self.size = 1


class MockOptions:
    "A mock scan options collection"

    def __init__(self, options):
        self.options = options
        self.options_dict = {o.name: o for o in options}

    def num_options(self):
        "Number of options"
        return len(self.options)

    def by_name(self, name):
        "Get option by name"
        return self.options_dict.get(name)

    def flatbed_selected(self, _handle):
        "Is flatbed selected?"
        return False

    def supports_paper(self, _paper, _tolerance):
        "Does it support the given paper?"
        return True


class MockDevice:
    "A mock scan device"

    def __init__(self, name, model="model", vendor="vendor"):
        self.name = name
        self.model = model
        self.vendor = vendor
        self.label = ""


class MockScan(Scan):
    "A mock Scan class"

    def __init__(self):
        # Initialize GObject to allow property access
        GObject.GObject.__init__(self)

        # Bypass Scan.__init__ logic by manually setting attributes
        self._device_list = []
        self.combobd = unittest.mock.Mock()
        self.combobd.get_num_rows.return_value = 0
        self.combobd_changed_signal = 1
        self.option_widgets = {}
        self._geometry_boxes = {}
        self.ignored_paper_formats = []
        self.profiles = {}
        self.combobsp = unittest.mock.Mock()
        self.combobsp.get_num_rows.return_value = 0
        self.combobsp_changed_signal = 1
        self.setting_profile = []
        self.setting_current_scan_options = []
        self.thread = unittest.mock.Mock()
        self.thread.device_handle = unittest.mock.Mock()
        self.framen = unittest.mock.Mock()
        self.scan_button = unittest.mock.Mock()
        self.combobp = unittest.mock.Mock()
        self.combobp.get_num_rows.return_value = 0
        self.scan_options = unittest.mock.Mock()

        self._available_scan_options = MockOptions([])

    # Mock methods that would otherwise interact with GUI or SANE
    def get_window(self):
        "Get the parent window"
        return None

    def emit(self, *args):
        "Mock emit method"
        return GObject.GObject.emit(self, *args)

    def save_current_profile(self, name):
        "Mock save_current_profile"
        self.profiles[name] = Profile()
        self._profile = name


class TestScanDialog:
    "Test Scan dialog edge cases"

    # FIXME: why is the logic strange here?
    def test_value_for_active_option(self):
        """Testing the strange logic of _value_for_active_option
        return not value and not opt.cap & enums.CAP_INACTIVE"""
        opt_active = MockOption("opt", enums.TYPE_BOOL, cap=0)
        opt_inactive = MockOption("opt", enums.TYPE_BOOL, cap=enums.CAP_INACTIVE)
        assert not _value_for_active_option(True, opt_active)
        assert _value_for_active_option(False, opt_active)
        assert not _value_for_active_option(False, opt_inactive)

    def test_do_profile_changed(self):
        "Test _do_profile_changed"
        scan = MockScan()
        combobsp = unittest.mock.Mock()
        combobsp.get_active_text.return_value = "new_profile"
        scan.profiles = {"new_profile": Profile()}
        scan._do_profile_changed(combobsp)
        assert scan.num_reloads == 0
        assert scan._profile == "new_profile"

    def test_set_device_unknown(self):
        "Test setting an unknown device"
        scan = MockScan()
        scan.emit = unittest.mock.Mock()
        scan.device_list = [MockDevice("dev1")]
        scan.set_device("unknown_dev")
        scan.emit.assert_called_with("process-error", "open_device", unittest.mock.ANY)

    def test_set_device_list_dedup(self):
        "Test setting device list with duplicate names/models"
        scan = MockScan()
        dev1 = MockDevice("dev1", "model1", "vendor1")
        dev2 = MockDevice("dev1", "model1", "vendor1")  # Duplicate name
        dev3 = MockDevice("dev2", "model1", "vendor1")  # Duplicate model

        scan.combobd = unittest.mock.Mock()
        scan.combobd.get_num_rows.return_value = 1

        scan.set_device_list([dev1, dev2, dev3])

        assert "on dev1" in dev1.label
        assert "on dev2" in dev3.label

        scan.combobd.insert_text.assert_any_call(0, dev1.label)
        scan.combobd.insert_text.assert_any_call(1, dev3.label)

    def test_pack_widget_units(self):
        "Test _pack_widget adds correct unit labels"
        scan = MockScan()

        units = [
            (enums.UNIT_PIXEL, "pel"),
            (enums.UNIT_BIT, "bit"),
            (enums.UNIT_MM, "mm"),
            (enums.UNIT_DPI, "ppi"),
            (enums.UNIT_PERCENT, "%"),
            (enums.UNIT_MICROSECOND, "μs"),
        ]

        for unit, text in units:
            opt = MockOption("opt", enums.TYPE_INT, unit=unit)
            widget = unittest.mock.Mock()
            hbox = unittest.mock.Mock()
            hboxp = unittest.mock.Mock()

            with unittest.mock.patch("dialog.scan.Gtk.Label") as mocklabel:
                scan._pack_widget(
                    widget, (scan._available_scan_options, opt, hbox, hboxp)
                )
                mocklabel.assert_called_with(label=text)

    def test_create_paper_widget_manual(self):
        "Test creating paper widget with 'Manual' selection"
        scan = MockScan()
        scan.combobp = None
        scan._geometry_boxes = {
            "br-x": unittest.mock.Mock(),
            "br-y": unittest.mock.Mock(),
            "tl-x": unittest.mock.Mock(),
            "tl-y": unittest.mock.Mock(),
            "page-height": unittest.mock.Mock(),
            "page-width": unittest.mock.Mock(),
        }

        hboxp = unittest.mock.Mock()

        with unittest.mock.patch("dialog.scan.ComboBoxText") as mockcombobox:
            mock_combo = mockcombobox.return_value
            mock_combo.get_active_text.return_value = "Manual"

            scan._create_paper_widget(MockOptions([]), hboxp)
            # Manually set because mockcombobox replaces the class,
            # returning a mock instance
            scan.combobp = mock_combo

            args, _ = mock_combo.connect.call_args
            callback = args[1]
            callback(None)

            scan._geometry_boxes["br-x"].show_all.assert_called()
            assert scan.paper is None

    def test_create_paper_widget_edit(self):
        "Test creating paper widget with 'Edit' selection"
        scan = MockScan()
        scan.combobp = None
        scan._geometry_boxes = {
            "br-x": 1,
            "br-y": 1,
            "tl-x": 1,
            "tl-y": 1,
            "page-height": 1,
            "page-width": 1,  # Needed for all() check
        }
        hboxp = unittest.mock.Mock()
        scan._edit_paper = unittest.mock.Mock()

        with unittest.mock.patch("dialog.scan.ComboBoxText") as mockcombobox:
            mock_combo = mockcombobox.return_value
            mock_combo.get_active_text.return_value = "Edit"

            scan._create_paper_widget(MockOptions([]), hboxp)
            scan.combobp = mock_combo

            args, _ = mock_combo.connect.call_args
            callback = args[1]
            callback(None)

            scan._edit_paper.assert_called()

    def test_update_options_recursion_limit(self):
        "Test update_options with recursion limit"
        scan = MockScan()
        scan.num_reloads = 10
        scan.reload_recursion_limit = 5
        scan.emit = unittest.mock.Mock()

        scan._update_options(MockOptions([]))

        scan.emit.assert_called_with(
            "process-error", "update_options", unittest.mock.ANY
        )

    def test_update_single_option_bool_false(self):
        "Test updating a single boolean option to False"
        scan = MockScan()
        opt = MockOption("opt", enums.TYPE_BOOL)
        widget = unittest.mock.Mock()
        widget.signal = "signal"  # Add signal attribute
        scan.option_widgets = {"opt": widget}
        scan.thread.device_handle.opt = False

        # _value_for_active_option(False, opt) -> True, so set_active(False) is called
        scan._update_single_option(opt)
        widget.set_active.assert_called_with(False)

    def test_update_single_option_entry(self):
        "Test updating a single string option in an Entry widget"
        scan = MockScan()
        opt = MockOption("opt", enums.TYPE_STRING)
        widget = unittest.mock.Mock(spec=Gtk.Entry)
        widget.signal = "signal"
        scan.option_widgets = {"opt": widget}
        scan.thread.device_handle.opt = ""  # Empty string is False-y

        scan._update_single_option(opt)
        widget.set_text.assert_called_with("")

    def test_update_option_mismatch(self):
        "Test updating option with mismatched name or type"
        scan = MockScan()
        opt = MockOption("opt", enums.TYPE_INT)
        widget = unittest.mock.Mock()
        scan.option_widgets = {"opt": widget}

        # Mismatch name
        new_opt_name = MockOption("other", enums.TYPE_INT)
        assert scan._update_option(opt, new_opt_name)

        # Mismatch type
        new_opt_type = MockOption("opt", enums.TYPE_BOOL)
        assert scan._update_option(opt, new_opt_type)

    def test_set_paper_formats_unsupported(self):
        "Test setting paper formats with unsupported paper"
        scan = MockScan()
        scan.combobp = unittest.mock.Mock()
        scan.combobp.get_num_rows.return_value = 0

        formats = {"A4": "data"}
        options = unittest.mock.Mock()
        options.supports_paper.return_value = False
        scan._available_scan_options = options

        scan._set_paper_formats(formats)

        assert "A4" in scan.ignored_paper_formats

    def test_set_paper_unsupported(self):
        "Test setting an unsupported paper size"
        scan = MockScan()
        scan.ignored_paper_formats = ["A4"]
        scan._paper = "A3"

        # Try setting unsupported paper
        scan._set_paper("A4")

        # Check that it didn't change the paper property
        # Since _paper is A3, and we tried A4, it should remain A3 or at least
        # not emit changed-paper for A4
        scan.emit = unittest.mock.Mock()
        scan._set_paper("A4")
        scan.emit.assert_not_called()

    def test_edit_paper(self):
        "Test editing paper size"
        scan = MockScan()
        scan.combobp = unittest.mock.Mock()
        scan.combobp.get_num_rows.return_value = 0
        scan.paper_formats = {"A4": {"x": 1, "y": 2, "l": 0, "t": 0}}
        scan.paper = "A4"

        with unittest.mock.patch(
            "dialog.scan.Dialog"
        ) as mockdialog, unittest.mock.patch(
            "dialog.scan.PaperList"
        ) as mockpaperlist, unittest.mock.patch(
            "dialog.scan.Gtk.Box"
        ):

            mock_window = mockdialog.return_value
            mock_window.get_content_area.return_value = unittest.mock.Mock()

            mock_slist = mockpaperlist.return_value
            mock_slist.data = [["A4", 1, 2, 0, 0]]

            scan._edit_paper()

    def test_add_profile_errors(self):
        "Test adding profiles with invalid inputs"
        scan = MockScan()
        scan._add_profile(None, Profile())  # No name
        scan._add_profile("name", None)  # No profile
        scan._add_profile("name", "not_a_profile")  # Invalid profile type
        assert len(scan.profiles) == 0

    def test_set_current_scan_options_errors(self):
        "Test setting current scan options with invalid inputs"
        scan = MockScan()
        scan.set_current_scan_options(None)
        scan.set_current_scan_options("not_a_profile")
        # Should just log errors and return

    def test_set_option_profile_errors(self):
        "Test setting option profile with invalid inputs"
        scan = MockScan()
        scan.combobp.get_num_rows.return_value = 0
        profile = unittest.mock.Mock()
        profile.each_frontend_option.return_value = []
        # Mock iterator to yield nothing immediately
        scan._set_option_profile(profile, iter([]))

        # Mock iterator yielding inactive option
        scan.available_scan_options = MockOptions(
            [MockOption("inactive", enums.TYPE_INT, cap=enums.CAP_INACTIVE)]
        )
        profile.get_backend_option_by_index.return_value = ("inactive", 10)

        scan._set_option_profile(profile, iter([1]))

    def test_update_widget_value_types(self):
        "Test updating widget values for different option types"
        scan = MockScan()

        # Switch/CheckButton
        opt = MockOption("bool", enums.TYPE_BOOL)
        widget = unittest.mock.Mock(spec=Gtk.CheckButton)
        widget.get_active.return_value = False
        widget.signal = "signal"
        scan.option_widgets = {"bool": widget}
        scan._update_widget_value(opt, True)
        widget.set_active.assert_called_with(True)

        # SpinButton
        opt = MockOption("int", enums.TYPE_INT)
        widget = unittest.mock.Mock(spec=Gtk.SpinButton)
        widget.get_value.return_value = 5
        widget.signal = "signal"
        scan.option_widgets = {"int": widget}
        scan._update_widget_value(opt, 10)
        widget.set_value.assert_called_with(10)

        # ComboBox
        opt = MockOption("combo", enums.TYPE_STRING, constraint=["a", "b"])
        widget = unittest.mock.Mock(spec=Gtk.ComboBox)
        widget.get_active.return_value = 0  # "a"
        widget.signal = "signal"
        scan.option_widgets = {"combo": widget}
        scan._update_widget_value(opt, "b")
        widget.set_active.assert_called_with(1)

    def test_get_xy_resolution_missing(self):
        "Test getting XY resolution when options are missing"
        scan = MockScan()
        scan._available_scan_options = None
        assert scan._get_xy_resolution() == (None, None)

        scan._available_scan_options = MockOptions([])
        # val() raises AttributeError if not found
        # MockOptions.val returns 0 by default but here we test absence
        # scan._available_scan_options.val = unittest.mock.Mock(side_effect=AttributeError)
        # x, y = scan._get_xy_resolution()
        # assert x == enums.POINTS_PER_INCH # Fallback

    def test_changed_scan_option_callback_adf(self):
        "Test changed scan option callback for ADF and Flatbed"
        scan = MockScan()
        scan.framen = unittest.mock.Mock()
        scan.adf_defaults_scan_all_pages = True

        options = MockOptions([MockOption("source", enums.TYPE_STRING)])
        scan._available_scan_options = options

        # Test ADF selection sets num_pages to 0
        bscannum = unittest.mock.Mock()
        scan._changed_scan_option_callback(None, "source", "ADF", None, bscannum)
        assert scan.num_pages == 0

        # Test Flatbed selection
        scan._changed_scan_option_callback(None, "source", "Flatbed", None, bscannum)
        # Should set num_pages = 1 if not allow_batch_flatbed (default False)

    def test_make_progress_string(self):
        "Test make_progress_string"
        assert "1 of 2" in make_progress_string(1, 2)
        assert "Scanning page 1" in make_progress_string(1, 0)

    def test_set_device_list_vendor(self):
        "Test set_device_list with vendor"
        scan = MockScan()
        dev = MockDevice("dev1", "model1", "vendor1")
        dev.vendor = "vendor1"
        scan.set_device_list([dev])
        assert "vendor1 model1" in dev.label

    def test_pack_widget_button(self):
        "Test _pack_widget with TYPE_BUTTON"
        scan = MockScan()
        opt = MockOption("opt", enums.TYPE_BUTTON)
        widget = unittest.mock.Mock()
        hbox = unittest.mock.Mock()
        hboxp = unittest.mock.Mock()
        scan._pack_widget(widget, (scan._available_scan_options, opt, hbox, hboxp))
        hbox.pack_end.assert_called_with(widget, True, True, 0)

    def test_update_widget_value_entry_empty(self):
        "Test _update_widget_value with Gtk.Entry and empty value"
        scan = MockScan()
        opt = MockOption("opt", enums.TYPE_STRING)
        widget = unittest.mock.Mock(spec=Gtk.Entry)
        widget.signal = "signal"
        scan.option_widgets = {"opt": widget}
        scan._update_widget_value(opt, "")
        widget.set_text.assert_called_with("")

    def test_new_val(self):
        "Test _new_val utility function"
        assert _new_val(1, 2)
        assert _new_val(None, 1)
        assert _new_val(1, None)
        assert not _new_val(1, 1)
        assert not _new_val(None, None)

    def test_allow_batch_flatbed(self):
        "Test allow_batch_flatbed property"
        scan = MockScan()
        scan.framen = unittest.mock.Mock()

        # Test True
        scan.allow_batch_flatbed = True
        scan.framen.set_sensitive.assert_called_with(True)

        # Test False with flatbed selected
        scan.framen.set_sensitive.reset_mock()
        scan.available_scan_options = unittest.mock.Mock()
        scan.available_scan_options.flatbed_selected.return_value = True
        scan.allow_batch_flatbed = False
        scan.framen.set_sensitive.assert_called_with(False)
        assert scan.num_pages == 1

    def test_get_xy_resolution_complex(self):
        "Test get_xy_resolution with multiple resolutions defined"
        scan = MockScan()
        options = unittest.mock.Mock()
        scan._available_scan_options = options

        # All resolutions defined
        options.val.side_effect = lambda name, handle: {
            "resolution": 300,
            "x-resolution": 0,
            "y-resolution": 0,
        }.get(name, 0)

        x, y = scan._get_xy_resolution()
        assert x == 300
        assert y == 300

        # xres, yres defined in current_scan_options
        scan.current_scan_options = unittest.mock.Mock()
        scan.current_scan_options.each_backend_option.return_value = [0, 1]
        scan.current_scan_options.get_backend_option_by_index.side_effect = [
            ("x-resolution", 600),
            ("y-resolution", 1200),
        ]
        options.val.side_effect = lambda name, handle: {
            "resolution": 300,
            "x-resolution": 1,
            "y-resolution": 1,
        }.get(name, 0)

        x, y = scan._get_xy_resolution()
        assert x == 600
        assert y == 1200

    def test_save_profile_callback(self):
        "Test _save_profile_callback"
        parent = MockScan()
        parent.profiles = {}

        with unittest.mock.patch(
            "dialog.scan.Gtk.Dialog"
        ) as mockdialogclass, unittest.mock.patch(
            "dialog.scan.Gtk.Entry"
        ) as mockentryclass, unittest.mock.patch(
            "dialog.scan.Gtk.Box"
        ), unittest.mock.patch(
            "dialog.scan.Gtk.Label"
        ):

            mock_dialog = mockdialogclass.return_value
            mock_dialog.run.return_value = Gtk.ResponseType.OK
            mock_dialog.get_content_area.return_value = unittest.mock.Mock()

            mock_entry = mockentryclass.return_value
            mock_entry.get_text.return_value = "New Profile"

            _save_profile_callback(None, parent)
            assert "New Profile" in parent.profiles

    def test_save_profile_callback_cancel(self):
        "Test cancelling _save_profile_callback"
        parent = MockScan()
        parent.profiles = {}

        with unittest.mock.patch(
            "dialog.scan.Gtk.Dialog"
        ) as mockdialogclass, unittest.mock.patch(
            "dialog.scan.Gtk.Entry"
        ) as mockentryclass, unittest.mock.patch(
            "dialog.scan.Gtk.Box"
        ), unittest.mock.patch(
            "dialog.scan.Gtk.Label"
        ):

            mock_dialog = mockdialogclass.return_value
            mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
            mock_dialog.get_content_area.return_value = unittest.mock.Mock()

            mock_entry = mockentryclass.return_value
            mock_entry.get_text.return_value = "New Profile"

            _save_profile_callback(None, parent)

    def test_edit_profile_callback(self):
        "Test _edit_profile_callback"
        parent = MockScan()
        parent.combobp.get_num_rows.return_value = 0
        parent.profiles = {"test": Profile()}
        parent._profile = "test"  # Manually set to avoid property setter side effects
        parent.available_scan_options = MockOptions([])

        with unittest.mock.patch(
            "dialog.scan.Gtk.Dialog"
        ) as mockdialogclass, unittest.mock.patch(
            "dialog.scan.Gtk.Label"
        ), unittest.mock.patch(
            "dialog.scan._build_profile_table"
        ):

            mock_dialog = mockdialogclass.return_value
            mock_dialog.run.return_value = Gtk.ResponseType.OK
            mock_dialog.get_content_area.return_value = unittest.mock.Mock()

            _edit_profile_callback(None, parent)
            parent.scan_options.assert_called()

    def test_edit_profile_callback_reloaded(self):
        "Test _edit_profile_callback and reloaded-scan-options"
        parent = MockScan()
        parent.combobp.get_num_rows.return_value = 0
        parent.profiles = {"test": Profile()}
        parent._profile = "test"
        parent.available_scan_options = MockOptions([])

        # Use real GObject emit for reloaded-scan-options
        def mock_scan_options(_device):
            parent.emit("reloaded-scan-options")

        parent.scan_options.side_effect = mock_scan_options
        parent.set_profile = unittest.mock.Mock()

        with unittest.mock.patch(
            "dialog.scan.Gtk.Dialog"
        ) as mockdialogclass, unittest.mock.patch(
            "dialog.scan.Gtk.Label"
        ), unittest.mock.patch(
            "dialog.scan._build_profile_table"
        ):

            mock_dialog = mockdialogclass.return_value
            mock_dialog.run.return_value = Gtk.ResponseType.OK
            mock_dialog.get_content_area.return_value = unittest.mock.Mock()

            _edit_profile_callback(None, parent)
            parent.set_profile.assert_called_with("test")

    def test_edit_profile_callback_no_name(self):
        "Test _edit_profile_callback with no profile name"
        parent = MockScan()
        parent.combobp.get_num_rows.return_value = 0
        parent._profile = None
        parent.current_scan_options = Profile()
        parent.available_scan_options = MockOptions([])
        parent.set_current_scan_options = unittest.mock.Mock()

        with unittest.mock.patch(
            "dialog.scan.Gtk.Dialog"
        ) as mockdialogclass, unittest.mock.patch(
            "dialog.scan.Gtk.Label"
        ), unittest.mock.patch(
            "dialog.scan._build_profile_table"
        ):

            mock_dialog = mockdialogclass.return_value
            mock_dialog.run.return_value = Gtk.ResponseType.OK
            mock_dialog.get_content_area.return_value = unittest.mock.Mock()

            _edit_profile_callback(None, parent)
            parent.set_current_scan_options.assert_called()

    def test_do_delete_profile_backend_item(self):
        "Test do_delete_profile_backend_item"
        profile = Profile()
        profile.add_backend_option("opt", 1)
        options = MockOptions([MockOption("opt", enums.TYPE_INT)])
        vbox = unittest.mock.Mock()
        frameb = unittest.mock.Mock()
        framef = unittest.mock.Mock()
        with unittest.mock.patch("dialog.scan._build_profile_table"):
            do_delete_profile_backend_item(
                None, [profile, options, vbox, frameb, framef, "opt", 0]
            )
        assert profile.num_backend_options() == 0

    def test_build_profile_table(self):
        "Test _build_profile_table"
        profile = Profile()
        profile.add_backend_option("opt", 1, 1)
        profile.add_frontend_option("fopt", "val")
        options = MockOptions([MockOption("opt", enums.TYPE_INT)])
        vbox = unittest.mock.Mock()
        vbox.show_all = unittest.mock.Mock()
        _build_profile_table(profile, options, vbox)
        vbox.show_all.assert_called()

    def test_set_paper_with_geometry(self):
        "Test _set_paper with geometry options"
        scan = MockScan()
        scan.combobp.get_num_rows.return_value = 0
        scan.paper_formats = {"A4": {"x": 210, "y": 297, "l": 0, "t": 0}}

        options = unittest.mock.Mock()
        opt = MockOption("page-height", enums.TYPE_INT)
        options.by_name.side_effect = lambda name: (
            opt if "page" in name else MockOption(name, enums.TYPE_INT)
        )
        options.supports_paper.return_value = True
        scan.available_scan_options = options
        scan._add_current_scan_options = unittest.mock.Mock()

        scan._set_paper("A4")
        scan._add_current_scan_options.assert_called()


def test_reproduce_bug(mocker, sane_scan_dialog, set_device_wait_reload):
    "Reproduce AttributeError: 'Dialog' object has no attribute 'parent'"

    # Mocking necessary parts to get the Scan dialog to load options and create the paper widget

    # 1. Mock SaneThread.do_get_devices
    def mocked_do_get_devices(_cls, _request):
        devices = [("mock_name", "", "", "")]
        return [
            SimpleNamespace(name=x[0], vendor=x[1], model=x[1], label=x[1])
            for x in devices
        ]

    mocker.patch("dialog.sane.SaneThread.do_get_devices", mocked_do_get_devices)

    # 2. Mock SaneThread.do_open_device
    def mocked_do_open_device(self, request):
        self.device_handle = SimpleNamespace(tl_x=0, tl_y=0, br_x=100, br_y=100)
        self.device = request.args[0]
        request.data(f"opened device '{self.device}'")

    mocker.patch("dialog.sane.SaneThread.do_open_device", mocked_do_open_device)

    # 3. Mock SaneThread.do_get_options
    # We need geometry options to trigger _create_paper_widget
    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            index=1,
            name="tl-x",
            title="Top-left x",
            desc="",
            type=2,
            unit=3,
            size=1,
            cap=5,
            constraint=(0, 215, 0),
        ),
        Option(
            index=2,
            name="tl-y",
            title="Top-left y",
            desc="",
            type=2,
            unit=3,
            size=1,
            cap=5,
            constraint=(0, 297, 0),
        ),
        Option(
            index=3,
            name="br-x",
            title="Bottom-right x",
            desc="",
            type=2,
            unit=3,
            size=1,
            cap=5,
            constraint=(0, 215, 0),
        ),
        Option(
            index=4,
            name="br-y",
            title="Bottom-right y",
            desc="",
            type=2,
            unit=3,
            size=1,
            cap=5,
            constraint=(0, 297, 0),
        ),
    ]

    def mocked_do_get_options(_self, _request):
        return raw_options

    mocker.patch("dialog.sane.SaneThread.do_get_options", mocked_do_get_options)

    # Use the dialog from fixture
    dialog = sane_scan_dialog

    # Use helper fixture to set device and wait for reload
    set_device_wait_reload(dialog, "mock_name")

    # Now combobp should be present
    assert hasattr(dialog, "combobp")
    assert dialog.combobp is not None

    # Setup paper formats so we have something to edit/remove
    dialog.paper_formats = {"TestPaper": {"x": 100, "y": 100, "l": 0, "t": 0}}

    # Find "Edit" index
    model = dialog.combobp.get_model()
    edit_index = -1
    for row in model:
        if row[0] == "Edit":
            edit_index = row.path[0]
            break

    assert edit_index != -1

    # Trigger Edit
    dialog.combobp.set_active(edit_index)

    # Wait for the dialog to be shown/processed.
    # _edit_paper is called synchronously from combobox changed signal.
    # The new dialog is created synchronously.

    # Inspect toplevel windows
    toplevels = Gtk.Window.list_toplevels()
    edit_window = None
    for win in toplevels:
        if win.get_title() == "Edit paper size":
            edit_window = win
            break

    assert edit_window is not None

    # Find the remove button
    def find_button_with_icon(container, icon_name):
        children = container.get_children()
        for child in children:
            if isinstance(child, Gtk.Button):
                image = child.get_image()
                if isinstance(image, Gtk.Image):
                    # In GTK3 get_icon_name might return None if set from stock or otherwise.
                    # The code uses Gtk.Image.new_from_icon_name("list-remove", ...)
                    storage_type = image.get_storage_type()
                    if storage_type == Gtk.ImageType.ICON_NAME:
                        if image.get_icon_name()[0] == icon_name:
                            return child
            if isinstance(child, Gtk.Container):
                found = find_button_with_icon(child, icon_name)
                if found:
                    return found
        return None

    rbutton = find_button_with_icon(edit_window, "list-remove")
    assert rbutton is not None

    # Click the remove button
    try:
        rbutton.clicked()
    except AttributeError as e:
        pytest.fail(f"Raised AttributeError: {e}")

    # If we get here, it passed
