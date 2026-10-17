"""dialogue for setting preferences."""

import logging
import pathlib
import shutil
from typing import ClassVar, cast

import gi

from scantpaper.comboboxtext import ComboBoxText
from scantpaper.dependencies import jbig2_available
from scantpaper.dialog import Dialog
from scantpaper.helpers import (
    chooser_path,
    configure_fractional_spinbutton,
    get_tmp_dir,
    pack_box,
    run_dialog,
    set_margins,
)
from scantpaper.i18n import _

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gio,
    GObject,
    Gtk,
)

logger = logging.getLogger(__name__)

UNIT_SLIDER_STEP = 0.001


class PreferencesDialog(Dialog):
    """dialogue for setting preferences."""

    __gsignals__: ClassVar[
        dict[str, tuple[GObject.SignalFlags, object, tuple[object, ...]]]
    ] = {
        "changed-preferences": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
    }
    settings: dict[str, object]

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise PreferencesDialog."""
        kwargs["title"] = _("Preferences")
        kwargs["hide_on_delete"] = True
        settings = kwargs.pop("settings")
        super().__init__(*args, **kwargs)
        self.settings = settings.copy()
        vbox = self.get_content_area()

        # Notebook for scan and general options
        notebook = Gtk.Notebook()
        vbox.append(notebook)
        notebook.set_vexpand(True)

        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.START)
        set_margins(vbox1, 0)
        self._add_scan_options(vbox1)
        notebook.append_page(vbox1, Gtk.Label(label=_("Scan options")))

        vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        set_margins(vbox2, 0)
        notebook.append_page(vbox2, Gtk.Label(label=_("General options")))
        self._add_general_options1(vbox2)
        self._add_general_options2(vbox2)

        self.add_actions([(_("_OK"), self._apply_callback), (_("_Cancel"), self.hide)])
        self.present()

    def _add_scan_options(self, vbox: Gtk.Box) -> None:
        self._cbo = Gtk.CheckButton(label=_("Open scanner at program start"))
        self._cbo.set_tooltip_text(
            _(
                "Automatically open the scan dialog in the background at program start. "
                "This saves time clicking the scan button and waiting for the "
                "program to find the list of scanners"
            )
        )
        if "auto-open-scan-dialog" in self.settings:
            self._cbo.set_active(self.settings["auto-open-scan-dialog"])
        vbox.append(self._cbo)
        self._cbo.set_vexpand(True)

        # Device blacklist
        hboxb = Gtk.Box()
        vbox.append(hboxb)
        label = Gtk.Label(label=_("Device blacklist"))
        hboxb.append(label)
        self._blacklist = Gtk.Entry()
        hboxb.append(self._blacklist)
        hboxb.set_tooltip_text(_("Device blacklist (regular expression)"))
        if (
            "device blacklist" in self.settings
            and self.settings["device blacklist"] is not None
        ):
            self._blacklist.set_text(self.settings["device blacklist"])

        # Cycle SANE handle after scan
        self._cbcsh = Gtk.CheckButton(label=_("Cycle SANE handle after scan"))
        self._cbcsh.set_tooltip_text(
            _("Some ADFs do not feed out the last page if this is not enabled")
        )
        if "cycle sane handle" in self.settings:
            self._cbcsh.set_active(self.settings["cycle sane handle"])
        vbox.append(self._cbcsh)

        # Allow batch scanning from flatbed
        self._cb_batch_flatbed = Gtk.CheckButton(
            label=_("Allow batch scanning from flatbed")
        )
        self._cb_batch_flatbed.set_tooltip_text(
            _(
                "If not set, switching to a flatbed scanner will force # pages to "
                "1 and single-sided mode."
            )
        )
        self._cb_batch_flatbed.set_active(self.settings["allow-batch-flatbed"])
        vbox.append(self._cb_batch_flatbed)

        # Ignore duplex capabilities
        self._cb_ignore_duplex = Gtk.CheckButton(
            label=_("Ignore duplex capabilities of scanner")
        )
        self._cb_ignore_duplex.set_tooltip_text(
            _(
                "If set, any duplex capabilities are ignored, and facing/reverse "
                "widgets are displayed to allow manual interleaving of pages."
            )
        )
        self._cb_ignore_duplex.set_active(self.settings["ignore-duplex-capabilities"])
        vbox.append(self._cb_ignore_duplex)

        # Force new scan job between pages
        self._cb_cancel_btw_pages = Gtk.CheckButton(
            label=_("Force new scan job between pages")
        )
        self._cb_cancel_btw_pages.set_tooltip_text(
            _(
                "Otherwise, some Brother scanners report out of documents, "
                "despite scanning from flatbed."
            )
        )
        self._cb_cancel_btw_pages.set_active(self.settings["cancel-between-pages"])
        vbox.append(self._cb_cancel_btw_pages)
        self._cb_cancel_btw_pages.set_sensitive(self.settings["allow-batch-flatbed"])
        self._cb_batch_flatbed.connect(
            "toggled",
            lambda _: self._cb_cancel_btw_pages.set_sensitive(
                self._cb_batch_flatbed.get_active()
            ),
        )

        # Select num-pages = all on selecting ADF
        self._cb_adf_all_pages = Gtk.CheckButton(
            label=_("Select # pages = all on selecting ADF")
        )
        self._cb_adf_all_pages.set_tooltip_text(
            _(
                "If this option is enabled, when switching to source=ADF, # pages = all is selected"
            )
        )
        self._cb_adf_all_pages.set_active(self.settings["adf-defaults-scan-all-pages"])
        vbox.append(self._cb_adf_all_pages)

        # Cache device list
        self._cb_cache_device_list = Gtk.CheckButton(label=_("Cache device list"))
        self._cb_cache_device_list.set_tooltip_text(
            _(
                "If this option is enabled, opening the scanner is quicker, "
                "as scantpaper does not first search for available devices."
            )
            + _(
                "This is only effective if the device names do not change between sessions."
            )
        )
        self._cb_cache_device_list.set_active(self.settings["cache-device-list"])
        vbox.append(self._cb_cache_device_list)

    def _add_general_options1(self, vbox: Gtk.Box) -> None:

        # Restore window setting
        self._cbw = Gtk.CheckButton(label=_("Restore window settings on startup"))
        self._cbw.set_active(self.settings["restore window"])
        vbox.append(self._cbw)
        self._cbw.set_vexpand(True)

        # View saved files
        self._cbv = Gtk.CheckButton(label=_("View files on saving"))
        self._cbv.set_active(self.settings["view files toggle"])
        vbox.append(self._cbv)
        self._cbv.set_vexpand(True)

        # Default filename
        hbox = Gtk.Box()
        vbox.append(hbox)
        hbox.set_vexpand(True)
        label = Gtk.Label(label=_("Default PDF & DjVu filename"))
        hbox.append(label)
        self._fileentry = Gtk.Entry()
        self._fileentry.set_tooltip_text(
            _("""strftime codes, e.g.:
%Y	current year

with the following additions:
%Da	author
%De	filename extension
%Dk	keywords
%Ds	subject
%Dt	title

All document date codes use strftime codes with a leading D, e.g.:
%DY	document year
%Dm	document month
%Dd	document day
""")
        )
        hbox.append(self._fileentry)
        self._fileentry.set_text(self.settings["default filename"])

        # Replace whitespace in filenames with underscores
        self._cbb = Gtk.CheckButton.new_with_label(
            _("Replace whitespace in filenames with underscores")
        )
        self._cbb.set_active(self.settings["convert whitespace to underscores"])
        vbox.append(self._cbb)
        self._cbb.set_vexpand(True)

        # Timezone
        self._cbtz = Gtk.CheckButton.new_with_label(_("Use timezone from locale"))
        self._cbtz.set_active(self.settings["use_timezone"])
        vbox.append(self._cbtz)
        self._cbtz.set_vexpand(True)

        # Time
        self._cbtm = Gtk.CheckButton.new_with_label(_("Specify time as well as date"))
        self._cbtm.set_active(self.settings["use_time"])
        vbox.append(self._cbtm)
        self._cbtm.set_vexpand(True)

        # Set file timestamp with metadata
        self._cbts = Gtk.CheckButton.new_with_label(
            _("Set access and modification times to metadata date")
        )
        self._cbts.set_active(self.settings["set_timestamp"])
        vbox.append(self._cbts)
        self._cbts.set_vexpand(True)

        # Temporary directory settings
        hbox = Gtk.Box()
        vbox.append(hbox)
        hbox.set_vexpand(True)
        label = Gtk.Label(label=_("Temporary directory"))
        hbox.append(label)
        self._tmpentry = Gtk.Entry()
        hbox.append(self._tmpentry)
        self._tmpentry.set_text(self.settings["TMPDIR"])
        button = Gtk.Button(label=_("Browse"))
        button.connect("clicked", self._choose_temp_dir)
        hbox.append(button)
        button.set_hexpand(True)

    def _choose_temp_dir(self, _button: Gtk.Button) -> None:
        file_chooser = Gtk.FileChooserDialog(
            title=_("Select temporary directory"),
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        file_chooser.add_buttons(
            _("Cancel"),
            Gtk.ResponseType.CANCEL,
            _("OK"),
            Gtk.ResponseType.OK,
        )
        file_chooser.set_current_folder(
            Gio.File.new_for_path(self._tmpentry.get_text())
        )
        if run_dialog(file_chooser) == Gtk.ResponseType.OK:
            self._tmpentry.set_text(
                get_tmp_dir(chooser_path(file_chooser), r"scantpaper-\w\w\w\w")
            )
        file_chooser.destroy()

    def _add_general_options2(self, vbox: Gtk.Box) -> None:

        # Available space in temporary directory
        hbox = Gtk.Box()
        pack_box(vbox, hbox, expand=True)
        label = Gtk.Label(label=_("Warn if available space less than (Mb)"))
        hbox.append(label)
        self._spinbuttonw = Gtk.SpinButton.new_with_range(0, 100_000, 1)
        self._spinbuttonw.set_value(self.settings["available-tmp-warning"])
        self._spinbuttonw.set_tooltip_text(
            _(
                "Warn if the available space in the temporary directory is less than this value"
            )
        )
        hbox.append(self._spinbuttonw)

        # Blank page standard deviation threshold
        hbox = Gtk.Box()
        pack_box(vbox, hbox, expand=True)
        label = Gtk.Label(label=_("Blank threshold"))
        hbox.append(label)
        self._spinbuttonb = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
        self._spinbuttonb.set_value(self.settings["Blank threshold"])
        self._spinbuttonb.set_tooltip_text(
            _("Threshold used for selecting blank pages")
        )
        configure_fractional_spinbutton(self._spinbuttonb, digits=3)
        hbox.append(self._spinbuttonb)

        # Dark page mean threshold
        hbox = Gtk.Box()
        pack_box(vbox, hbox, expand=True)
        label = Gtk.Label(label=_("Dark threshold"))
        hbox.append(label)
        self._spinbuttond = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
        self._spinbuttond.set_value(self.settings["Dark threshold"])
        self._spinbuttond.set_tooltip_text(_("Threshold used for selecting dark pages"))
        configure_fractional_spinbutton(self._spinbuttond, digits=3)
        hbox.append(self._spinbuttond)

        # OCR output
        hbox = Gtk.Box()
        pack_box(vbox, hbox, expand=True)
        label = Gtk.Label(label=_("OCR output"))
        hbox.append(label)
        ocr_function = [
            [
                "replace",
                _("Replace"),
                _(
                    "Replace the contents of the text buffer with that from the OCR output."
                ),
            ],
            ["prepend", _("Prepend"), _("Prepend the OCR output to the text buffer.")],
            ["append", _("Append"), _("Append the OCR output to the text buffer.")],
        ]
        self._comboo = ComboBoxText(data=ocr_function)
        self._comboo.set_active_index(self.settings["OCR output"])
        pack_box(hbox, self._comboo, expand=True)

        self._add_bilevel_compression(vbox)

        # Manage user-defined tools
        frame = Gtk.Frame(label=_("Manage user-defined tools"))
        pack_box(vbox, frame, expand=True)
        self._vboxt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame.set_child(self._vboxt)
        for tool in cast("list[object]", self.settings["user_defined_tools"]):
            self._add_user_defined_tool_entry(cast("str", tool))
        abutton = Gtk.Button()
        abutton.set_child(Gtk.Image.new_from_icon_name("list-add"))
        pack_box(self._vboxt, abutton, expand=True)
        abutton.connect("clicked", self._clicked_add_udt)

    def _add_bilevel_compression(self, vbox: Gtk.Box) -> None:
        """Add the codec preference for bilevel pages under automatic compression."""
        hbox = Gtk.Box()
        vbox.append(hbox)
        hbox.set_vexpand(True)
        label = Gtk.Label(label=_("Bilevel compression"))
        hbox.append(label)
        bilevel_function = [
            [
                "g4",
                _("Group 4"),
                _("Compress bilevel images with CCITT Group 4 encoding."),
            ],
        ]
        if jbig2_available():
            bilevel_function.append(
                [
                    "jb2",
                    _("JBIG2"),
                    _("Compress bilevel images with JBIG2 encoding."),
                ]
            )
        self._combobc = ComboBoxText(data=bilevel_function)
        self._combobc.set_active_index(self.settings["bilevel compression"])
        hbox.append(self._combobc)
        self._combobc.set_hexpand(True)

    def _clicked_add_udt(self, button: Gtk.Button) -> None:
        self._add_user_defined_tool_entry("my-tool %i %o")
        children = list(self._vboxt.observe_children())
        if children:
            self._vboxt.reorder_child_after(button, children[-1])

    def _add_user_defined_tool_entry(self, tool: str) -> None:
        """Add user-defined tool entry."""
        hbox = Gtk.Box()
        self._vboxt.append(hbox)
        hbox.set_vexpand(True)
        entry = Gtk.Entry()
        entry.set_text(tool)
        entry.set_tooltip_text(
            _(
                """Use %%i and %%o for the input and output filenames respectively,
or a single %%i if the image is to be modified in-place.

The other variable available is:
%%r resolution"""
            )
            % ()
        )
        hbox.append(entry)
        entry.set_hexpand(True)
        button = Gtk.Button.new_with_mnemonic(label=_("_Delete"))

        def delete_udt(_widget: Gtk.Button) -> None:
            self._vboxt.remove(hbox)

        button.connect("clicked", delete_udt)
        hbox.append(button)
        hbox.show()

    def _apply_callback(self) -> None:
        # Validate user-defined tools before hiding
        tools = []
        for hbox in list(self._vboxt.observe_children()):
            if (
                isinstance(hbox, Gtk.Box)
                and hbox.get_orientation() == Gtk.Orientation.HORIZONTAL
            ):
                for widget in list(hbox.observe_children()):
                    if isinstance(widget, Gtk.Entry):
                        text = widget.get_text()
                        tools.append(text)

        invalid_tools = []
        for tool in tools:
            if tool.strip():
                executable = tool.strip().split()[0]
                if shutil.which(executable) is None:
                    invalid_tools.append(tool)
            else:
                invalid_tools.append(tool)

        if invalid_tools:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                destroy_with_parent=True,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("The following user-defined tools could not be found:\n")
                + "\n".join(invalid_tools)
                + "\n\n"
                + _("Please check that the command is installed and in your PATH."),
            )
            dialog.set_title(_("User-defined tool not found"))
            run_dialog(dialog)
            dialog.destroy()
            return

        self.hide()

        self.settings["auto-open-scan-dialog"] = self._cbo.get_active()
        self.settings["device blacklist"] = self._blacklist.get_text()
        self.settings["cycle sane handle"] = self._cbcsh.get_active()
        self.settings["allow-batch-flatbed"] = self._cb_batch_flatbed.get_active()
        self.settings["cancel-between-pages"] = self._cb_cancel_btw_pages.get_active()
        self.settings["adf-defaults-scan-all-pages"] = (
            self._cb_adf_all_pages.get_active()
        )
        self.settings["cache-device-list"] = self._cb_cache_device_list.get_active()
        self.settings["ignore-duplex-capabilities"] = (
            self._cb_ignore_duplex.get_active()
        )
        self.settings["default filename"] = self._fileentry.get_text()
        self.settings["restore window"] = self._cbw.get_active()
        self.settings["use_timezone"] = self._cbtz.get_active()
        self.settings["use_time"] = self._cbtm.get_active()
        self.settings["set_timestamp"] = self._cbts.get_active()
        self.settings["convert whitespace to underscores"] = self._cbb.get_active()
        self.settings["available-tmp-warning"] = self._spinbuttonw.get_value()
        self.settings["Blank threshold"] = self._spinbuttonb.get_value()
        self.settings["Dark threshold"] = self._spinbuttond.get_value()
        self.settings["OCR output"] = self._comboo.get_active_index()
        self.settings["bilevel compression"] = self._combobc.get_active_index()

        self.settings["user_defined_tools"] = tools

        # Store viewer preferences
        self.settings["view files toggle"] = self._cbv.get_active()

        # Expand tildes in the filename
        newdir = get_tmp_dir(
            str(pathlib.Path(self._tmpentry.get_text()).expanduser()),
            r"scantpaper-\w\w\w\w",
        )
        self.settings["TMPDIR"] = newdir
        self.emit("changed-preferences", self.settings)
