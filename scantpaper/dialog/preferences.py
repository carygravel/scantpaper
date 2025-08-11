"dialogue for setting preferences"

import logging
import pathlib
import gi
from comboboxtext import ComboBoxText
from dialog import Dialog
from i18n import _
from helpers import get_tmp_dir

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)

UNIT_SLIDER_STEP = 0.001


class PreferencesDialog(Dialog):
    "dialogue for setting preferences"

    __gsignals__ = {
        "changed-preferences": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),
        ),
    }
    settings = None

    def __init__(self, *args, **kwargs):
        kwargs["title"] = _("Preferences")
        kwargs["hide_on_delete"] = True
        settings = kwargs.pop("settings")
        super().__init__(*args, **kwargs)
        self.settings = settings.copy()
        vbox = self.get_content_area()

        # Notebook for scan and general options
        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)

        vbox1 = Gtk.VBox()
        vbox1.set_border_width(self.get_border_width())
        self._add_scan_options(vbox1)
        notebook.append_page(vbox1, Gtk.Label(label=_("Scan options")))

        vbox2 = Gtk.VBox()
        vbox2.set_border_width(self.get_border_width())
        notebook.append_page(vbox2, Gtk.Label(label=_("General options")))
        self._add_general_options1(vbox2)
        self._add_general_options2(vbox2)

        self.add_actions(
            [("gtk-ok", self._preferences_apply_callback), ("gtk-cancel", self.hide)]
        )
        self.show_all()

    def _add_scan_options(self, vbox):
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
        vbox.pack_start(self._cbo, True, True, 0)

        # Device blacklist
        hboxb = Gtk.HBox()
        vbox.pack_start(hboxb, False, False, 0)
        label = Gtk.Label(label=_("Device blacklist"))
        hboxb.pack_start(label, False, False, 0)
        self._blacklist = Gtk.Entry()
        hboxb.add(self._blacklist)
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
        vbox.pack_start(self._cbcsh, False, False, 0)

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
        vbox.pack_start(self._cb_batch_flatbed, False, False, 0)

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
        vbox.pack_start(self._cb_ignore_duplex, False, False, 0)

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
        vbox.pack_start(self._cb_cancel_btw_pages, False, False, 0)
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
        vbox.pack_start(self._cb_adf_all_pages, False, False, 0)

        # Cache device list
        self._cb_cache_device_list = Gtk.CheckButton(label=_("Cache device list"))
        self._cb_cache_device_list.set_tooltip_text(
            _(
                "If this option is enabled, opening the scanner is quicker, "
                "as gscan2pdf does not first search for available devices."
            )
            + _(
                "This is only effective if the device names do not change between sessions."
            )
        )
        self._cb_cache_device_list.set_active(self.settings["cache-device-list"])
        vbox.pack_start(self._cb_cache_device_list, False, False, 0)

    def _add_general_options1(self, vbox):

        # Restore window setting
        self._cbw = Gtk.CheckButton(label=_("Restore window settings on startup"))
        self._cbw.set_active(self.settings["restore window"])
        vbox.pack_start(self._cbw, True, True, 0)

        # View saved files
        self._cbv = Gtk.CheckButton(label=_("View files on saving"))
        self._cbv.set_active(self.settings["view files toggle"])
        vbox.pack_start(self._cbv, True, True, 0)

        # Default filename
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Default PDF & DjVu filename"))
        hbox.pack_start(label, False, False, 0)
        self._fileentry = Gtk.Entry()
        self._fileentry.set_tooltip_text(
            _(
                """strftime codes, e.g.:
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
"""
            )
        )
        hbox.add(self._fileentry)
        self._fileentry.set_text(self.settings["default filename"])

        # Replace whitespace in filenames with underscores
        self._cbb = Gtk.CheckButton.new_with_label(
            _("Replace whitespace in filenames with underscores")
        )
        self._cbb.set_active(self.settings["convert whitespace to underscores"])
        vbox.pack_start(self._cbb, True, True, 0)

        # Timezone
        self._cbtz = Gtk.CheckButton.new_with_label(_("Use timezone from locale"))
        self._cbtz.set_active(self.settings["use_timezone"])
        vbox.pack_start(self._cbtz, True, True, 0)

        # Time
        self._cbtm = Gtk.CheckButton.new_with_label(_("Specify time as well as date"))
        self._cbtm.set_active(self.settings["use_time"])
        vbox.pack_start(self._cbtm, True, True, 0)

        # Set file timestamp with metadata
        self._cbts = Gtk.CheckButton.new_with_label(
            _("Set access and modification times to metadata date")
        )
        self._cbts.set_active(self.settings["set_timestamp"])
        vbox.pack_start(self._cbts, True, True, 0)

        # Temporary directory settings
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Temporary directory"))
        hbox.pack_start(label, False, False, 0)
        self._tmpentry = Gtk.Entry()
        hbox.add(self._tmpentry)
        self._tmpentry.set_text(self.settings["TMPDIR"])
        button = Gtk.Button(label=_("Browse"))
        button.connect("clicked", self._choose_temp_dir)
        hbox.pack_end(button, True, True, 0)

    def _choose_temp_dir(self, _button):
        file_chooser = Gtk.FileChooserDialog(
            title=_("Select temporary directory"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_current_folder(self._tmpentry.get_text())
        if file_chooser.run() == Gtk.ResponseType.OK:
            self._tmpentry.set_text(
                get_tmp_dir(file_chooser.get_filename(), r"gscan2pdf-\w\w\w\w")
            )
        file_chooser.destroy()

    def _add_general_options2(self, vbox):

        # Available space in temporary directory
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Warn if available space less than (Mb)"))
        hbox.pack_start(label, False, False, 0)
        self._spinbuttonw = Gtk.SpinButton.new_with_range(0, 100_000, 1)
        self._spinbuttonw.set_value(self.settings["available-tmp-warning"])
        self._spinbuttonw.set_tooltip_text(
            _(
                "Warn if the available space in the temporary directory is less than this value"
            )
        )
        hbox.add(self._spinbuttonw)

        # Blank page standard deviation threshold
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Blank threshold"))
        hbox.pack_start(label, False, False, 0)
        self._spinbuttonb = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
        self._spinbuttonb.set_value(self.settings["Blank threshold"])
        self._spinbuttonb.set_tooltip_text(
            _("Threshold used for selecting blank pages")
        )
        hbox.add(self._spinbuttonb)

        # Dark page mean threshold
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Dark threshold"))
        hbox.pack_start(label, False, False, 0)
        self._spinbuttond = Gtk.SpinButton.new_with_range(0, 1, UNIT_SLIDER_STEP)
        self._spinbuttond.set_value(self.settings["Dark threshold"])
        self._spinbuttond.set_tooltip_text(_("Threshold used for selecting dark pages"))
        hbox.add(self._spinbuttond)

        # OCR output
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("OCR output"))
        hbox.pack_start(label, False, False, 0)
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
        hbox.pack_end(self._comboo, True, True, 0)

        # Manage user-defined tools
        frame = Gtk.Frame(label=_("Manage user-defined tools"))
        vbox.pack_start(frame, True, True, 0)
        self._vboxt = Gtk.VBox()
        self._vboxt.set_border_width(self.get_border_width())
        frame.add(self._vboxt)
        for tool in self.settings["user_defined_tools"]:
            self._add_user_defined_tool_entry(tool)
        abutton = Gtk.Button()
        abutton.set_image(Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
        self._vboxt.pack_start(abutton, True, True, 0)
        abutton.connect("clicked", self._clicked_add_udt)

    def _clicked_add_udt(self, button):
        self._add_user_defined_tool_entry("my-tool %i %o")
        self._vboxt.reorder_child(button, -1)

    def _add_user_defined_tool_entry(self, tool):
        "Add user-defined tool entry"
        hbox = Gtk.HBox()
        self._vboxt.pack_start(hbox, True, True, 0)
        entry = Gtk.Entry()
        entry.set_text(tool)
        entry.set_tooltip_text(
            _(
                """Use %i and %o for the input and output filenames respectively,
or a single %i if the image is to be modified in-place.

The other variable available is:
%r resolution"""
            )
        )
        hbox.pack_start(entry, True, True, 0)
        button = Gtk.Button.new_with_mnemonic(label=_("_Delete"))

        def delete_udt():
            hbox.destroy()

        button.connect("clicked", delete_udt)
        hbox.pack_end(button, False, False, 0)
        hbox.show_all()

    def _preferences_apply_callback(self):
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

        # Update list of user-defined tools
        tools = []
        for hbox in self._vboxt.get_children():
            if isinstance(hbox, Gtk.HBox):
                for widget in hbox.get_children():
                    if isinstance(widget, Gtk.Entry):
                        text = widget.get_text()
                        tools.append(text)
        self.settings["user_defined_tools"] = tools

        # Store viewer preferences
        self.settings["view files toggle"] = self._cbv.get_active()

        # Expand tildes in the filename
        newdir = get_tmp_dir(
            str(pathlib.Path(self._tmpentry.get_text()).expanduser()),
            r"gscan2pdf-\w\w\w\w",
        )
        self.settings["TMPDIR"] = newdir
        self.emit("changed-preferences", self.settings)
