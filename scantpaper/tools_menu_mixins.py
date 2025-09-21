"provide methods called from tools menu"

import datetime
import re
import logging
import gi
from comboboxtext import ComboBoxText
from const import PERCENT, VERSION, _90_DEGREES, _180_DEGREES, _100_PERCENT
from dialog import Dialog
from dialog.crop import Crop
from dialog.save import Save as SaveDialog
from file_menu_mixins import launch_default_for_file
from helpers import exec_command, expand_metadata_pattern, collate_metadata
from i18n import _
from postprocess_controls import OCRControls

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gdk,
    GLib,
    Gtk,
)

logger = logging.getLogger(__name__)


class ToolsMenuMixins:
    "provide methods called from tools menu"

    def rotate_90(self, _action, _param):
        "Rotates the selected pages by 90 degrees"
        self._rotate(
            -_90_DEGREES,
            self.slist.indices2pages(self.slist.get_selected_indices()),
        )

    def rotate_180(self, _action, _param):
        "Rotates the selected pages by 180 degrees"
        self._rotate(
            _180_DEGREES,
            self.slist.indices2pages(self.slist.get_selected_indices()),
        )

    def rotate_270(self, _action, _param):
        "Rotates the selected pages by 270 degrees"
        self._rotate(
            _90_DEGREES,
            self.slist.indices2pages(self.slist.get_selected_indices()),
        )

    def _rotate(self, angle, pagelist):
        "Rotate selected images"
        for page in pagelist:
            self.slist.rotate(
                angle=angle,
                page=page,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=self.post_process_progress.finish,
                error_callback=self._error_callback,
                display_callback=self._display_callback,
            )

    def threshold(self, _action, _param):
        "Display page selector and on apply threshold accordingly"
        windowt = Dialog(
            transient_for=self,
            title=_("Threshold"),
        )

        # Frame for page range
        windowt.add_page_range()

        # SpinButton for threshold
        hboxt = Gtk.HBox()
        vbox = windowt.get_content_area()
        vbox.pack_start(hboxt, False, True, 0)
        label = Gtk.Label(label=_("Threshold"))
        hboxt.pack_start(label, False, True, 0)
        labelp = Gtk.Label(label=PERCENT)
        hboxt.pack_end(labelp, False, True, 0)
        spinbutton = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbutton.set_value(self.settings["threshold tool"])
        hboxt.pack_end(spinbutton, False, True, 0)

        def threshold_apply_callback():
            self.settings["threshold tool"] = spinbutton.get_value()
            self.settings["Page range"] = windowt.page_range
            pagelist = self.slist.get_page_index(
                self.settings["Page range"], self._error_callback
            )
            if not pagelist:
                return
            page = 0
            for i in pagelist:
                page += 1

                def threshold_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.threshold(
                    threshold=self.settings["threshold tool"],
                    page=self.slist.data[i][2],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=threshold_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )

        windowt.add_actions(
            [
                ("gtk-apply", threshold_apply_callback),
                ("gtk-cancel", windowt.destroy),
            ]
        )
        windowt.show_all()

    def brightness_contrast(self, _action, _param):
        "Display page selector and on apply brightness & contrast accordingly"
        windowt = Dialog(
            transient_for=self,
            title=_("Brightness / Contrast"),
        )
        hbox, label = None, None

        # Frame for page range
        windowt.add_page_range()

        # SpinButton for brightness
        hbox = Gtk.HBox()
        vbox = windowt.get_content_area()
        vbox.pack_start(hbox, False, True, 0)
        label = Gtk.Label(label=_("Brightness"))
        hbox.pack_start(label, False, True, 0)
        label = Gtk.Label(label=PERCENT)
        hbox.pack_end(label, False, True, 0)
        spinbuttonb = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbuttonb.set_value(self.settings["brightness tool"])
        hbox.pack_end(spinbuttonb, False, True, 0)

        # SpinButton for contrast
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, True, 0)
        label = Gtk.Label(label=_("Contrast"))
        hbox.pack_start(label, False, True, 0)
        label = Gtk.Label(label=PERCENT)
        hbox.pack_end(label, False, True, 0)
        spinbuttonc = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbuttonc.set_value(self.settings["contrast tool"])
        hbox.pack_end(spinbuttonc, False, True, 0)

        def brightness_contrast_callback():
            self.settings["brightness tool"] = spinbuttonb.get_value()
            self.settings["contrast tool"] = spinbuttonc.get_value()
            self.settings["Page range"] = windowt.page_range
            pagelist = self.slist.get_page_index(
                self.settings["Page range"], self._error_callback
            )
            if not pagelist:
                return
            for i in pagelist:

                def brightness_contrast_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.brightness_contrast(
                    brightness=self.settings["brightness tool"],
                    contrast=self.settings["contrast tool"],
                    page=self.slist.data[i][2],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=brightness_contrast_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )

        windowt.add_actions(
            [
                ("gtk-apply", brightness_contrast_callback),
                ("gtk-cancel", windowt.destroy),
            ]
        )
        windowt.show_all()

    def negate(self, _action, _param):
        "Display page selector and on apply negate accordingly"
        windowt = Dialog(
            transient_for=self,
            title=_("Negate"),
        )

        # Frame for page range
        windowt.add_page_range()

        def negate_callback():
            self.settings["Page range"] = windowt.page_range
            pagelist = self.slist.get_page_index(
                self.settings["Page range"], self._error_callback
            )
            if not pagelist:
                return
            for i in pagelist:

                def negate_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.negate(
                    page=self.slist.data[i][2],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=negate_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )

        windowt.add_actions(
            [("gtk-apply", negate_callback), ("gtk-cancel", windowt.destroy)]
        )
        windowt.show_all()

    def unsharp(self, _action, _param):
        "Display page selector and on apply unsharp accordingly"
        windowum = Dialog(
            transient_for=self,
            title=_("Unsharp mask"),
        )

        # Frame for page range

        windowum.add_page_range()
        spinbuttonr = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        spinbuttons = Gtk.SpinButton.new_with_range(0, 2 * _100_PERCENT, 1)
        spinbuttont = Gtk.SpinButton.new_with_range(0, _100_PERCENT, 1)
        layout = [
            [
                _("Radius"),
                spinbuttonr,
                _("pixels"),
                self.settings["unsharp radius"],
                _("Blur Radius."),
            ],
            [
                _("Percentage"),
                spinbuttons,
                _("%"),
                self.settings["unsharp percentage"],
                _("Unsharp strength, in percent."),
            ],
            [
                _("Threshold"),
                spinbuttont,
                None,
                self.settings["unsharp threshold"],
                _(
                    "Threshold controls the minimum brightness change that will be sharpened."
                ),
            ],
        ]

        # grid for layout
        grid = Gtk.Grid()
        vbox = windowum.get_content_area()
        vbox.pack_start(grid, True, True, 0)
        for i, row in enumerate(layout):
            col = 0
            hbox = Gtk.HBox()
            label = Gtk.Label(label=row[col])
            grid.attach(hbox, col, i, 1, 1)
            col += 1
            hbox.pack_start(label, False, True, 0)
            hbox = Gtk.HBox()
            hbox.pack_end(row[col], True, True, 0)
            grid.attach(hbox, col, i, 1, 1)
            col += 1
            if col in row:
                hbox = Gtk.HBox()
                grid.attach(hbox, col, i, 1, 1)
                label = Gtk.Label(label=row[col])
                hbox.pack_start(label, False, True, 0)

            col += 1
            if col in row:
                row[1].set_value(row[col])

            col += 1
            row[1].set_tooltip_text(row[col])

        def unsharp_callback():
            self.settings["unsharp radius"] = spinbuttonr.get_value()
            self.settings["unsharp percentage"] = int(spinbuttons.get_value())
            self.settings["unsharp threshold"] = int(spinbuttont.get_value())
            self.settings["Page range"] = windowum.page_range
            pagelist = self.slist.get_page_index(
                self.settings["Page range"], self._error_callback
            )
            if not pagelist:
                return
            for i in pagelist:

                def unsharp_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.unsharp(
                    page=self.slist.data[i][2],
                    radius=self.settings["unsharp radius"],
                    percent=self.settings["unsharp percentage"],
                    threshold=self.settings["unsharp threshold"],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=unsharp_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )

        windowum.add_actions(
            [("gtk-apply", unsharp_callback), ("gtk-cancel", windowum.destroy)]
        )
        windowum.show_all()

    def crop_dialog(self, _action, _param):
        "Display page selector and on apply crop accordingly"
        if self._windowc is not None:
            self._windowc.present()
            return

        width, height = self._current_page.get_size()
        self._windowc = Crop(transient_for=self, page_width=width, page_height=height)

        def on_changed_selection(_widget, selection):
            # copy required here because somehow the garbage collection
            # destroys the Gdk.Rectangle too early and afterwards, the
            # contents are corrupt.
            self.settings["selection"] = selection.copy()
            self.view.handler_block(self.view.selection_changed_signal)
            self.view.set_selection(selection)
            self.view.handler_unblock(self.view.selection_changed_signal)

        self._windowc.connect("changed-selection", on_changed_selection)

        if self.settings["selection"]:
            self._windowc.selection = self.settings["selection"]

        def crop_callback():
            self.settings["Page range"] = self._windowc.page_range
            self.crop_selection(
                None,  # action
                None,  # param
                self.slist.get_page_index(
                    self.settings["Page range"], self._error_callback
                ),
            )

        self._windowc.add_actions(
            [("gtk-apply", crop_callback), ("gtk-cancel", self._windowc.hide)]
        )
        self._windowc.show_all()

    def crop_selection(self, _action, _param, pagelist=None):
        "Crop the selected area of the specified pages."
        if not self.settings["selection"]:
            return

        if not pagelist:
            pagelist = self.slist.get_selected_indices()

        if not pagelist:
            return

        for i in pagelist:

            def crop_finished_callback(response):
                self.post_process_progress.finish(response)

            self.slist.crop(
                page=self.slist.data[i][2],
                x=self.settings["selection"].x,
                y=self.settings["selection"].y,
                w=self.settings["selection"].width,
                h=self.settings["selection"].height,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=crop_finished_callback,
                error_callback=self._error_callback,
                display_callback=self._display_callback,
            )

    def split_dialog(self, _action, _param):
        "Display page selector and on apply crop accordingly"

        # Until we have a separate tool for the divider, kill the whole
        #        sub { $windowsp->hide }
        #    if ( defined $windowsp ) {
        #        $windowsp->present;
        #        return;
        #    }

        windowsp = Dialog(
            transient_for=self,
            title=_("Split"),
            hide_on_delete=True,
        )

        # Frame for page range
        windowsp.add_page_range()
        hbox = Gtk.HBox()
        vbox = windowsp.get_content_area()
        vbox.pack_start(hbox, False, False, 0)
        label = Gtk.Label(label=_("Direction"))
        hbox.pack_start(label, False, True, 0)
        direction = [
            [
                "v",
                _("Vertically"),
                _("Split the page vertically into left and right pages."),
            ],
            [
                "h",
                _("Horizontally"),
                _("Split the page horizontally into top and bottom pages."),
            ],
        ]
        combob = ComboBoxText(data=direction)
        width, height = self._current_page.get_size()
        sb_pos = Gtk.SpinButton.new_with_range(0, width, 1)

        def changed_split_direction(_widget):
            if direction[combob.get_active()][0] == "v":
                sb_pos.set_range(0, width)
            else:
                sb_pos.set_range(0, height)
            self._update_view_position(
                direction[combob.get_active()][0], sb_pos.get_value(), width, height
            )

        combob.connect("changed", changed_split_direction)
        combob.set_active_index("v")
        hbox.pack_end(combob, False, True, 0)

        # SpinButton for position
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, True, 0)
        label = Gtk.Label(label=_("Position"))
        hbox.pack_start(label, False, True, 0)
        hbox.pack_end(sb_pos, False, True, 0)
        sb_pos.connect(
            "value-changed",
            lambda _: self._update_view_position(
                direction[combob.get_active()][0], sb_pos.get_value(), width, height
            ),
        )
        sb_pos.set_value(width / 2)

        def changed_split_position_selection(_widget, sel):
            if sel:
                if direction[combob.get_active()][0] == "v":
                    sb_pos.set_value(sel.x + sel.width)
                else:
                    sb_pos.set_value(sel.y + sel.height)

        self.view.position_changed_signal = self.view.connect(
            "selection-changed", changed_split_position_selection
        )

        def split_apply_callback():
            self.settings["split-direction"] = direction[combob.get_active()][0]
            self.settings["split-position"] = sb_pos.get_value()
            self.settings["Page range"] = windowsp.page_range
            pagelist = self.slist.get_page_index(
                self.settings["Page range"], self._error_callback
            )
            if not pagelist:
                return
            page = 0
            for i in pagelist:
                page += 1

                def split_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.split_page(
                    direction=self.settings["split-direction"],
                    position=self.settings["split-position"],
                    page=self.slist.data[i][2],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=split_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )

        def split_cancel_callback():
            self.view.disconnect(self.view.position_changed_signal)
            windowsp.destroy()

        windowsp.add_actions(
            [
                ("gtk-apply", split_apply_callback),
                (
                    "gtk-cancel",
                    # Until we have a separate tool for the divider, kill the whole
                    #        sub { $windowsp->hide }
                    split_cancel_callback,
                ),
            ]
        )
        windowsp.show_all()

    def _update_view_position(self, direction, position, width, height):
        "Updates the view's selection rectangle based on the given direction and dimensions."
        selection = Gdk.Rectangle()
        if direction == "v":
            selection.width = position
            selection.height = height
        else:
            selection.width = width
            selection.height = position
        self.view.set_selection(selection)

    def unpaper_dialog(self, _action, _param):
        "Run unpaper to clean up scan."
        if self._windowu is not None:
            self._windowu.present()
            return

        self._windowu = Dialog(
            transient_for=self,
            title=_("unpaper"),
            hide_on_delete=True,
        )

        # Frame for page range
        self._windowu.add_page_range()

        # add unpaper options
        vbox = self._windowu.get_content_area()
        self._unpaper.add_options(vbox)

        def unpaper_apply_callback():

            # Update $self.settings
            self.settings["unpaper options"] = self._unpaper.get_options()
            self.settings["Page range"] = self._windowu.page_range

            # run unpaper
            pagelist = self.slist.indices2pages(
                self.slist.get_page_index(
                    self.settings["Page range"], self._error_callback
                )
            )
            if not pagelist:
                return

            for pageobject in pagelist:

                def unpaper_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.unpaper(
                    page=pageobject,
                    options={
                        "command": self._unpaper.get_cmdline(),
                        "direction": self._unpaper.get_option("direction"),
                    },
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=unpaper_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )
            self._windowu.hide()

        self._windowu.add_actions(
            [("gtk-ok", unpaper_apply_callback), ("gtk-cancel", self._windowu.hide)]
        )
        self._windowu.show_all()

    def ocr_dialog(self, _action, _parma):
        "Run OCR on current page and display result"
        if self._windowo is not None:
            self._windowo.present()
            return

        self._windowo = Dialog(
            transient_for=self,
            title=_("OCR"),
            hide_on_delete=True,
        )

        # Frame for page range
        self._windowo.add_page_range()

        # OCR engine selection
        ocr_controls = OCRControls(
            available_engines=self._ocr_engine,
            engine=self.settings["ocr engine"],
            language=self.settings["ocr language"],
            active=self.settings["OCR on scan"],
            threshold=self.settings["threshold-before-ocr"],
            threshold_value=self.settings["threshold tool"],
        )
        vbox = self._windowo.get_content_area()
        vbox.pack_start(ocr_controls, False, True, 0)

        def ocr_apply_callback():
            self._run_ocr(
                ocr_controls.engine,
                ocr_controls.language,
                ocr_controls.threshold,
                ocr_controls.threshold_value,
            )

        self._windowo.add_actions(
            [("gtk-ok", ocr_apply_callback), ("gtk-cancel", self._windowo.hide)]
        )
        self._windowo.show_all()

    def _run_ocr(self, engine, tesslang, threshold_flag, threshold):
        "Run OCR on a set of pages"
        if engine == "tesseract":
            self.settings["ocr language"] = tesslang

        kwargs = {
            "queued_callback": self.post_process_progress.queued,
            "started_callback": self.post_process_progress.update,
            "running_callback": self.post_process_progress.update,
            "finished_callback": self._ocr_finished_callback,
            "error_callback": self._error_callback,
            "display_callback": self._ocr_display_callback,
            "engine": engine,
            "language": self.settings["ocr language"],
        }
        self.settings["ocr engine"] = engine
        self.settings["threshold-before-ocr"] = threshold_flag
        if threshold_flag:
            self.settings["threshold tool"] = threshold
            kwargs["threshold"] = threshold

        # fill pagelist with filenames
        # depending on which radiobutton is active
        self.settings["Page range"] = self._windowo.page_range
        pagelist = self.slist.indices2pages(
            self.slist.get_page_index(self.settings["Page range"], self._error_callback)
        )
        if not pagelist:
            return
        kwargs["pages"] = pagelist
        self.slist.ocr_pages(**kwargs)
        self._windowo.hide()

    def _ocr_finished_callback(self, response):
        "Callback function to be executed when OCR processing is finished."
        self.post_process_progress.finish(response)

    def _ocr_display_callback(self, response):
        "Callback function to handle the display of OCR (Optical Character Recognition) results."
        uuid = response.request.args[0]["page"]
        i = self.slist.find_page_by_uuid(uuid)
        if i is None:
            logger.error("Can't display page with uuid %s: page not found", uuid)
        else:
            page = self.slist.get_selected_indices()
            if page and i == page[0]:
                self._create_txt_canvas(self.slist.data[i][2])

    def user_defined_dialog(self, _action, _param):
        "Displays a dialog for selecting and applying user-defined tools."
        windowudt = Dialog(
            transient_for=self,
            title=_("User-defined tools"),
            hide_on_delete=True,
        )

        # Frame for page range
        windowudt.add_page_range()
        hbox = Gtk.HBox()
        vbox = windowudt.get_content_area()
        vbox.pack_start(hbox, False, False, 0)
        label = Gtk.Label(label=_("Selected tool"))
        hbox.pack_start(label, False, True, 0)
        self._pref_udt_cmbx = self._add_udt_combobox(hbox)

        def udt_apply_callback():
            self.settings["Page range"] = windowudt.page_range
            pagelist = self.slist.indices2pages(
                self.slist.get_page_index(
                    self.settings["Page range"], self._error_callback
                )
            )
            if not pagelist:
                return
            self.settings["current_udt"] = self._pref_udt_cmbx.get_active_text()

            for page in pagelist:

                def user_defined_finished_callback(response):
                    self.post_process_progress.finish(response)

                self.slist.user_defined(
                    page=page,
                    command=self.settings["current_udt"],
                    queued_callback=self.post_process_progress.queued,
                    started_callback=self.post_process_progress.update,
                    running_callback=self.post_process_progress.update,
                    finished_callback=user_defined_finished_callback,
                    error_callback=self._error_callback,
                    display_callback=self._display_callback,
                )
            windowudt.hide()

        windowudt.add_actions(
            [("gtk-ok", udt_apply_callback), ("gtk-cancel", windowudt.hide)]
        )
        windowudt.show_all()

    def email(self, _action, _param):
        "Display page selector and email."
        if self._windowe is not None:
            self._windowe.present()
            return

        self._windowe = SaveDialog(
            transient_for=self,
            title=_("Email as PDF"),
            hide_on_delete=True,
            page_range=self.settings["Page range"],
            include_time=self.settings["use_time"],
            meta_datetime=datetime.datetime.now() + self.settings["datetime offset"],
            select_datetime=bool(self.settings["datetime offset"]),
            meta_title=self.settings["title"],
            meta_title_suggestions=self.settings["title-suggestions"],
            meta_author=self.settings["author"],
            meta_author_suggestions=self.settings["author-suggestions"],
            meta_subject=self.settings["subject"],
            meta_subject_suggestions=self.settings["subject-suggestions"],
            meta_keywords=self.settings["keywords"],
            meta_keywords_suggestions=self.settings["keywords-suggestions"],
            jpeg_quality=self.settings["quality"],
            downsample_dpi=self.settings["downsample dpi"],
            downsample=self.settings["downsample"],
            pdf_compression=self.settings["pdf compression"],
            text_position=self.settings["text_position"],
            pdf_font=self.settings["pdf font"],
            can_encrypt_pdf="pdftk" in self._dependencies,
        )

        # Frame for page range
        self._windowe.add_page_range()

        # PDF options
        self._windowe.add_pdf_options()

        def email_callback():

            # Set options
            self._windowe.update_config_dict(self.settings)

            # Compile list of pages
            self.settings["Page range"] = self._windowe.page_range
            uuids = self._list_of_page_uuids()

            # dig out the compression
            self.settings["downsample"] = self._windowe.downsample
            self.settings["downsample dpi"] = self._windowe.downsample_dpi
            self.settings["pdf compression"] = self._windowe.pdf_compression
            self.settings["quality"] = self._windowe.jpeg_quality

            # Compile options
            options = {
                "compression": self.settings["pdf compression"],
                "downsample": self.settings["downsample"],
                "downsample dpi": self.settings["downsample dpi"],
                "quality": self.settings["quality"],
                "text_position": self.settings["text_position"],
                "font": self.settings["pdf font"],
                "user-password": self._windowe.pdf_user_password,
            }
            filename = expand_metadata_pattern(
                template=self.settings["default filename"],
                convert_whitespace=self.settings["convert whitespace to underscores"],
                author=self.settings["author"],
                title=self.settings["title"],
                docdate=self._windowe.meta_datetime,
                today_and_now=datetime.datetime.now(),
                extension="pdf",
                subject=self.settings["subject"],
                keywords=self.settings["keywords"],
            )
            if re.search(r"^\s+$", filename, re.MULTILINE | re.DOTALL | re.VERBOSE):
                filename = "document"
            self._pdf_email = f"{self.session.name}/{filename}.pdf"

            # Create the PDF
            def email_finished_callback(response):
                self.post_process_progress.finish(response)
                self.slist.thread.send("set_saved", uuids)
                if (
                    "view files toggle" in self.settings
                    and self.settings["view files toggle"]
                ):
                    launch_default_for_file(self._pdf_email)

                status = exec_command(["xdg-email", "--attach", self._pdf_email, "x@y"])
                if status:
                    self._show_message_dialog(
                        parent=self,
                        message_type="error",
                        buttons=Gtk.ButtonsType.CLOSE,
                        text=_("Error creating email"),
                    )

            self.slist.save_pdf(
                path=self._pdf_email,
                list_of_pages=uuids,
                metadata=collate_metadata(self.settings, datetime.datetime.now()),
                options=options,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=email_finished_callback,
                error_callback=self._error_callback,
            )
            self._windowe.hide()

        self._windowe.add_actions(
            [("gtk-ok", email_callback), ("gtk-cancel", self._windowe.hide)]
        )
        self._windowe.show_all()

    def about(self, _action, _param):
        "Display about dialog"
        about = Gtk.AboutDialog()

        # Gtk.AboutDialog->set_url_hook ($func, $data=undef);
        # Gtk.AboutDialog->set_email_hook ($func, $data=undef);

        about.set_program_name(GLib.get_application_name())
        about.set_version(VERSION)
        authors = [
            "Frederik Elwert",
            "Klaus Ethgen",
            "Andy Fingerhut",
            "Leon Fisk",
            "John Goerzen",
            "Alistair Grant",
            "David Hampton",
            "Sascha Hunold",
            "Jason Kankiewicz",
            "Matthijs Kooijman",
            "Peter Marschall",
            "Chris Mayo",
            "Hiroshi Miura",
            "Petr Písař",
            "Pablo Saratxaga",
            "Torsten Schönfeld",
            "Roy Shahbazian",
            "Jarl Stefansson",
            "Wikinaut",
            "Jakub Wilk",
            "Sean Dreilinger",
        ]
        about.set_authors(["Jeff Ratcliffe"])
        about.add_credit_section("Patches gratefully received from", authors)
        about.set_comments(_("To aid the scan-to-PDF process"))
        about.set_copyright(_("Copyright 2006--2025 Jeffrey Ratcliffe"))
        licence = """gscan2pdf --- to aid the scan to PDF or DjVu process
    Copyright 2006 -- 2025 Jeffrey Ratcliffe <jffry@posteo.net>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the version 3 GNU General Public License as
    published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
    """
        about.set_license(licence)
        about.set_website("http://gscan2pdf.sf.net")
        translators = """Yuri Chornoivan
    Davidmp
    Whistle
    Dušan Kazik
    Cédric VALMARY (Tot en òc)
    Eric Spierings
    Milo Casagrande
    Raúl González Duque
    R120X
    NSV
    Alexandre Prokoudine
    Aputsiaĸ Niels Janussen
    Paul Wohlhart
    Pierre Slamich
    Tiago Silva
    Igor Zubarev
    Jarosław Ogrodnik
    liorda
    Clopy
    Daniel Nylander
    csola
    dopais
    Po-Hsu Lin
    Tobias Bannert
    Ettore Atalan
    Eric Brandwein
    Mikhail Novosyolov
    rodroes
    morodan
    Hugues Drolet
    Martin Butter
    Albano Battistella
    Olesya Gerasimenko
    Pavel Borecki
    Stephan Woidowski
    Jonatan Nyberg
    Berov
    Utku BERBEROĞLU
    Arthur Rodrigues
    Matthias Sprau
    Buckethead
    Eugen Artus
    Quentin PAGÈS
    Alexandre NICOLADIE
    Aleksandr Proklov
    Silvio Brera
    papoteur
    """
        about.set_translator_credits(translators)
        about.set_artists(["lodp, Andreas E."])
        about.set_logo_icon_name("gscan2pdf")
        about.set_transient_for(self)
        about.run()
        about.destroy()
