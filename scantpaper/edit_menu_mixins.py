"provide methods called from edit menu"

import logging
import datetime
import re
import gi
from const import MAX_DPI
from dialog import Dialog
from dialog.renumber import Renumber
from dialog.preferences import PreferencesDialog
from i18n import _, d_sane

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


class EditMenuMixins:
    "provide methods called from edit menu"

    def undo(self, _action, _param):
        "Restore previous snapshot"
        logger.info("Undoing")
        self.slist.undo()

        # Update menus/buttons
        self._update_uimanager()

    def unundo(self, _action, _param):
        "Restore next snapshot"
        logger.info("Redoing")
        self.slist.unundo()

        # Update menus/buttons
        self._update_uimanager()

    def properties(self, _action, _param):
        "Display and manage the properties dialog for setting X and Y resolution."
        if self._windowp is not None:
            self._windowp.present()
            return

        self._windowp = Dialog(
            transient_for=self,
            title=_("Properties"),
            hide_on_delete=True,
        )
        vbox = self._windowp.get_content_area()
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=d_sane("X Resolution"))
        hbox.pack_start(label, False, False, 0)
        xspinbutton = Gtk.SpinButton.new_with_range(0, MAX_DPI, 1)
        xspinbutton.set_digits(1)
        hbox.pack_start(xspinbutton, True, True, 0)
        label = Gtk.Label(label=_("dpi"))
        hbox.pack_end(label, False, False, 0)
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=d_sane("Y Resolution"))
        hbox.pack_start(label, False, False, 0)
        yspinbutton = Gtk.SpinButton.new_with_range(0, MAX_DPI, 1)
        yspinbutton.set_digits(1)
        hbox.pack_start(yspinbutton, True, True, 0)
        label = Gtk.Label(label=_("dpi"))
        hbox.pack_end(label, False, False, 0)
        xresolution, yresolution = self.slist.get_selected_properties()
        xspinbutton.set_value(xresolution)
        yspinbutton.set_value(yresolution)

        def selection_changed_callback():
            xresolution, yresolution = self.slist.get_selected_properties()
            xspinbutton.set_value(xresolution)
            yspinbutton.set_value(yresolution)

        self.slist.get_selection().connect("changed", selection_changed_callback)

        def properties_apply_callback():
            self._windowp.hide()
            xresolution = xspinbutton.get_value()
            yresolution = yspinbutton.get_value()
            self.slist.get_model().handler_block(self.slist.row_changed_signal)
            for i in self.slist.get_selected_indices():
                logger.debug(
                    "setting resolution %s,%s for page %s",
                    xresolution,
                    yresolution,
                    self.slist.data[i][0],
                )
                self.slist.data[i][2].resolution = (
                    xresolution,
                    yresolution,
                    "PixelsPerInch",
                )

            self.slist.get_model().handler_unblock(self.slist.row_changed_signal)

        self._windowp.add_actions(
            [("gtk-ok", properties_apply_callback), ("gtk-cancel", self._windowp.hide)]
        )
        self._windowp.show_all()

    def cut_selection(self, _action, _param):
        "Cut the selection"
        self.slist.clipboard = self.slist.cut_selection()
        self._update_uimanager()

    def copy_selection(self, _action, _param):
        "Copy the selection"
        self.slist.clipboard = self.slist.copy_selection()
        self._update_uimanager()

    def paste_selection(self, _action, _param):
        "Paste the selection"
        if self.slist.clipboard is None:
            return
        pages = self.slist.get_selected_indices()
        if pages:
            self.slist.paste_selection(
                data=self.slist.clipboard,
                dest=pages[-1],
                how="after",
                select_new_pages=True,
            )
        else:
            self.slist.paste_selection(data=self.slist.clipboard, select_new_pages=True)
        self._update_uimanager()

    def delete_selection(self, _action, _param):
        "Delete the selected scans"
        self.slist.delete_selection_extra()

        # Reset start page in scan dialog
        if self._windows:
            self._windows.reset_start_page()
        self._update_uimanager()

    def renumber_dialog(self, _action, _param):
        "Dialog for renumber"
        dialog = Renumber(
            transient_for=self,
            document=self.slist,
            hide_on_delete=False,
        )
        dialog.connect(
            "error",
            lambda msg: self._show_message_dialog(
                parent=dialog,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=msg,
            ),
        )
        dialog.show_all()

    def select_all(self, _action, _param):
        "Select all scans"
        # if ($textview -> has_focus) {
        #  my ($start, $end) = $textbuffer->get_bounds;
        #  $textbuffer->select_range ($start, $end);
        # }
        # else {

        self.slist.get_selection().select_all()

        # }

    def select_odd_even(self, odd):
        "Select all odd(0) or even(1) scans"
        selection = []
        for i, row in enumerate(self.slist.data):
            if row[0] % 2 ^ odd:
                selection.append(i)

        self.slist.get_selection().unselect_all()
        self.slist.select(selection)

    def select_invert(self, _action, _param):
        "Invert selection"
        selection = self.slist.get_selected_indices()
        inverted = []
        for i in range(len(self.slist.data)):
            if i not in selection:
                inverted.append(i)
        self.slist.get_selection().unselect_all()
        self.slist.select(inverted)

    def select_modified_since_ocr(self, _action, _param):
        "Selects pages that have been modified since the last OCR process."
        selection = []
        for i, row in enumerate(self.slist.data):
            page = row[2]
            dirty_time = (
                page.dirty_time
                if hasattr(page, "dirty_time")
                else datetime.datetime(1970, 1, 1)
            )
            ocr_time = (
                page.ocr_time
                if hasattr(page, "ocr_time")
                else datetime.datetime(1970, 1, 1)
            )
            ocr_flag = page.ocr_flag if hasattr(page, "ocr_flag") else False
            if ocr_flag and (ocr_time <= dirty_time):
                selection.append(i)

        self.slist.get_selection().unselect_all()
        self.slist.select(selection)

    def select_no_ocr(self, _action, _param):
        "Select pages with no ocr output"
        selection = []
        for i, row in enumerate(self.slist.data):
            if not hasattr(row[2], "text_layer") or row[2].text_layer is None:
                selection.append(i)

        self.slist.get_selection().unselect_all()
        self.slist.select(selection)

    def clear_ocr(self, _action, _param):
        "Clear the OCR output from selected pages"

        # Clear the existing canvas
        self.t_canvas.clear_text()
        selection = self.slist.get_selected_indices()
        for i in selection:
            self.slist.data[i][2].text_layer = None

    def select_blank(self, _action, _param):
        "Analyse and select blank pages"
        self.analyse(True, False)

    def _select_odd(self, _action, _param):
        "Selects odd-numbered pages"
        self.select_odd_even(0)

    def _select_even(self, _action, _param):
        "Selects even-numbered pages"
        self.select_odd_even(1)

    def select_blank_pages(self):
        "Select blank pages"
        for page in self.slist.data:

            # compare Std Dev to threshold
            # std_dev is a list -- 1 value per channel
            if (
                sum(page[2].std_dev) / len(page[2].std_dev)
                <= self.settings["Blank threshold"]
            ):
                self.slist.select(page)
                logger.info("Selecting blank page")
            else:
                self.slist.unselect(page)
                logger.info("Unselecting non-blank page")

            logger.info(
                "StdDev: %s threshold: %s",
                page[2].std_dev,
                self.settings["Blank threshold"],
            )

    def select_dark(self, _action, _param):
        "Analyse and select dark pages"
        self.analyse(False, True)

    def select_dark_pages(self):
        "Select dark pages"
        for page in self.slist.data:

            # compare Mean to threshold
            # mean is a list -- 1 value per channel
            if (
                sum(page[2].mean) / len(page[2].std_dev)
                <= self.settings["Dark threshold"]
            ):
                self.slist.select(page)
                logger.info("Selecting dark page")
            else:
                self.slist.unselect(page)
                logger.info("Unselecting non-dark page")

            logger.info(
                "mean: %s threshold: %s",
                page[2].mean,
                self.settings["Dark threshold"],
            )

    def analyse(self, select_blank, select_dark):
        "Analyse selected images"

        pages_to_analyse = []
        for row in self.slist.data:
            page = row[2]
            dirty_time = (
                page.dirty_time
                if hasattr(page, "dirty_time")
                else datetime.datetime(1970, 1, 1)
            )
            analyse_time = (
                page.analyse_time
                if hasattr(page, "analyse_time")
                else datetime.datetime(1970, 1, 1)
            )
            if analyse_time <= dirty_time:
                logger.info(
                    "Updating: %s analyse_time: %s dirty_time: %s",
                    row[0],
                    analyse_time,
                    dirty_time,
                )
                pages_to_analyse.append(page.uuid)

        if len(pages_to_analyse) > 0:

            def analyse_finished_callback(response):
                self.post_process_progress.finish(response)
                if select_blank:
                    self.select_blank_pages()
                if select_dark:
                    self.select_dark_pages()

            self.slist.analyse(
                list_of_pages=pages_to_analyse,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=analyse_finished_callback,
                error_callback=self._error_callback,
            )

        else:
            if select_blank:
                self.select_blank_pages()
            if select_dark:
                self.select_dark_pages()

    def preferences(self, _action, _param):
        "Preferences dialog"
        if self._windowr is not None:
            self._windowr.present()
            return

        self._windowr = PreferencesDialog(transient_for=self, settings=self.settings)
        self._windowr.connect("changed-preferences", self._changed_preferences)
        self._windowr.show_all()

    def _changed_preferences(self, _widget, settings):
        logger.debug("Preferences changed %s", settings)

        if settings["device blacklist"] != self.settings["device blacklist"]:
            try:
                re.search(settings["device blacklist"], "dummy_device")
            except re.error:
                msg = _("Invalid regex. Try without special characters such as '*'")
                logger.warning(msg)
                self._show_message_dialog(
                    parent=self,
                    message_type="error",
                    buttons=Gtk.ButtonsType.CLOSE,
                    text=msg,
                    store_response=True,
                )
                settings["device blacklist"] = self.settings["device blacklist"]

        if self._windows:
            self._windows.cycle_sane_handle = self.settings["cycle sane handle"]
            self._windows.cancel_between_pages = self.settings["cancel-between-pages"]
            self._windows.allow_batch_flatbed = self.settings["allow-batch-flatbed"]
            self._windows.ignore_duplex_capabilities = self.settings[
                "ignore-duplex-capabilities"
            ]

        if self._windowi:
            self._windowi.include_time = self.settings["use_time"]

        self._update_list_user_defined_tools([self._pref_udt_cmbx, self._scan_udt_cmbx])

        if settings["TMPDIR"] != self.settings["TMPDIR"]:
            self.settings = settings
            response = self._ask_question(
                parent=self,
                type="question",
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=_("Changes will only take effect after restarting gscan2pdf.")
                + " "
                + _("Restart gscan2pdf now?"),
            )
            if response == Gtk.ResponseType.OK:
                self._restart()
        self.settings = settings

    def _update_list_user_defined_tools(self, combobox_array):
        for combobox in combobox_array:
            if combobox is not None:
                while combobox.get_num_rows() > 0:
                    combobox.remove(0)

        for tool in self.settings["user_defined_tools"]:
            for combobox in combobox_array:
                if combobox is not None:
                    combobox.append_text(tool)

        self._update_post_save_hooks()
        for combobox in combobox_array:
            if combobox is not None:
                combobox.set_active_by_text(self.settings["current_udt"])
