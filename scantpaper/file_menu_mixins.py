"provide methods called from file menu"

import datetime
import re
import os
import fcntl
import glob
import logging
import sys
import tempfile
import gi
from comboboxtext import ComboBoxText
import config
from const import ASTERISK, EMPTY, EMPTY_LIST, VERSION
from dialog.save import Save as SaveDialog
from helpers import exec_command, expand_metadata_pattern, collate_metadata
from i18n import _
from print_operation import PrintOperation

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gtk  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


def add_filter(file_chooser, name, file_extensions):
    "Create a file filter to show only supported file types in FileChooser dialog"
    ffilter = Gtk.FileFilter()
    for extension in file_extensions:
        pattern = []

        # Create case insensitive pattern
        for char in extension:
            pattern.append("[" + char.upper() + char.lower() + "]")

        ffilter.add_pattern("*." + EMPTY.join(pattern))

    types = None
    for ext in file_extensions:
        if types is not None:
            types += f", *.{ext}"

        else:
            types = f"*.{ext}"

    ffilter.set_name(f"{name} ({types})")
    file_chooser.add_filter(ffilter)
    ffilter = Gtk.FileFilter()
    ffilter.add_pattern("*")
    ffilter.set_name("All files")
    file_chooser.add_filter(ffilter)


def file_exists(chooser, filename):
    "Check if a file exists and prompt the user for confirmation if it does."

    if os.path.isfile(filename):

        # File exists; get the file chooser to ask the user to confirm.
        chooser.set_filename(filename)

        # Give the name change a chance to take effect
        GLib.idle_add(lambda: chooser.response(Gtk.ResponseType.OK))
        return True

    return False


def launch_default_for_file(filename):
    "Launch default viewer for file"
    uri = GLib.filename_to_uri(os.path.abspath(filename), None)
    logger.info("Opening %s via default launcher", uri)
    context = Gio.AppLaunchContext()
    try:
        Gio.AppInfo.launch_default_for_uri(uri, context)
    except Gio.Error as e:
        logger.error("Unable to launch viewer: %s", e)


class FileMenuMixins:
    "provide methods called from file menu"

    def new_(self, _action, _param):
        "Deletes all scans after warning"
        if not self._pages_saved(
            _("Some pages have not been saved.\nDo you really want to clear all pages?")
        ):
            return

        # in certain circumstances, before v2.5.5, having deleted one of several
        # pages, pressing the new button would cause some sort of race condition
        # between the tied array of the self.slist and the callbacks displaying the
        # thumbnails, so block this whilst clearing the array.
        self.slist.get_model().handler_block(self.slist.row_changed_signal)
        self.slist.get_selection().handler_block(self.slist.selection_changed_signal)

        # Depopulate the thumbnail list
        self.slist.data = []

        # Unblock self.slist signals now finished
        self.slist.get_selection().handler_unblock(self.slist.selection_changed_signal)
        self.slist.get_model().handler_unblock(self.slist.row_changed_signal)

        # Now we have to clear everything manually
        self.slist.get_selection().unselect_all()
        self.view.set_pixbuf(None)
        self.t_canvas.clear_text()
        self.a_canvas.clear_text()
        self._current_page = None

        # Reset start page in scan dialog
        self._windows.reset_start_page()

    def open_dialog(self, _action, _param):
        "Throw up file selector and open selected file"
        # cd back to cwd to get filename
        os.chdir(self.settings["cwd"])
        file_chooser = Gtk.FileChooserDialog(
            title=_("Open image"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_select_multiple(True)
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(self.settings["cwd"])
        add_filter(
            file_chooser,
            _("Image files"),
            [
                "jpg",
                "png",
                "pnm",
                "ppm",
                "pbm",
                "gif",
                "tif",
                "tiff",
                "pdf",
                "djvu",
                "ps",
                "gs2p",
            ],
        )
        if file_chooser.run() == Gtk.ResponseType.OK:

            # cd back to tempdir to import
            os.chdir(self.session.name)

            filenames = file_chooser.get_filenames()
            file_chooser.destroy()

            # Update cwd
            self.settings["cwd"] = os.path.dirname(filenames[0])
            self._import_files(filenames)
        else:
            file_chooser.destroy()

        # cd back to tempdir
        os.chdir(self.session.name)

    def _select_pagerange_callback(self, info):
        dialog = Gtk.Dialog(
            title=_("Pages to extract"),
            transient_for=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.add_buttons(
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
        )
        vbox = dialog.get_content_area()
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("First page to extract"))
        hbox.pack_start(label, False, False, 0)
        spinbuttonf = Gtk.SpinButton.new_with_range(1, info["pages"], 1)
        hbox.pack_end(spinbuttonf, False, False, 0)
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label=_("Last page to extract"))
        hbox.pack_start(label, False, False, 0)
        spinbuttonl = Gtk.SpinButton.new_with_range(1, info["pages"], 1)
        spinbuttonl.set_value(info["pages"])
        hbox.pack_end(spinbuttonl, False, False, 0)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            return int(spinbuttonf.get_value()), int(spinbuttonl.get_value())
        return None, None

    def _import_files_password_callback(self, filename):
        "Ask for password for encrypted PDF"
        text = _("Enter user password for PDF %s") % (filename)
        dialog = Gtk.MessageDialog(
            self,
            ["destroy-with-parent", "modal"],
            "question",
            Gtk.ButtonsType.OK_CANCEL,
            text,
        )
        dialog.set_title(text)
        vbox = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_invisible_char(ASTERISK)
        vbox.pack_end(entry, False, False, 0)
        dialog.show_all()
        response = dialog.run()
        text = entry.get_text()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and text != EMPTY:
            return text
        return None

    def _import_files_finished_callback(self, response):
        "import_files finished callback"
        logger.debug("finished import_files(%s)", response)
        self.post_process_progress.finish(response)

    def _import_files_metadata_callback(self, metadata):
        "Update the metadata from the imported file"
        logger.debug("import_files_metadata_callback(%s)", metadata)
        for dialog in (self._windowi, self._windowe):
            if dialog is not None:
                dialog.update_from_import_metadata(metadata)
        config.update_config_from_imported_metadata(self.settings, metadata)

    def _import_files(self, filenames, all_pages=False):
        "Import given files"
        # FIXME: import_files() now returns an array of pids.
        options = {
            "paths": filenames,
            "password_callback": self._import_files_password_callback,
            "queued_callback": self.post_process_progress.queued,
            "started_callback": self.post_process_progress.update,
            "running_callback": self.post_process_progress.update,
            "finished_callback": self._import_files_finished_callback,
            "metadata_callback": self._import_files_metadata_callback,
            "error_callback": self._error_callback,
        }
        if all_pages:
            options["pagerange_callback"] = lambda info: (1, info["pages"])
        else:
            options["pagerange_callback"] = self._select_pagerange_callback

        self.slist.import_files(**options)

    def _open_session_action(self, _action, _param):
        "open session"
        file_chooser = Gtk.FileChooserDialog(
            title=_("Open crashed session"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(self.settings["cwd"])
        if file_chooser.run() == Gtk.ResponseType.OK:
            filename = file_chooser.get_filenames()
            self._open_session(filename[0])

        file_chooser.destroy()

    def _open_session(self, sesdir):
        "open session"
        logger.info("Restoring session in %s", self.session)
        self.slist.open_session(
            dir=sesdir, delete=False, error_callback=self._error_callback
        )

    def save_dialog(self, _action, _param):
        "Display page selector and on save a fileselector."
        if self._windowi is not None:
            self._windowi.present()
            return

        image_types = [
            "pdf",
            "gif",
            "jpg",
            "png",
            "pnm",
            "ps",
            "tif",
            "txt",
            "hocr",
            "session",
        ]
        if self._dependencies["pdfunite"]:
            image_types.extend(["prependpdf", "appendpdf"])

        if self._dependencies["djvu"]:
            image_types.append("djvu")
        ps_backends = []
        for backend in ["libtiff", "pdf2ps", "pdftops"]:
            if self._dependencies[backend]:
                ps_backends.append(backend)

        self._windowi = SaveDialog(
            transient_for=self,
            title=_("Save"),
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
            image_types=image_types,
            image_type=self.settings["image type"],
            ps_backends=ps_backends,
            jpeg_quality=self.settings["quality"],
            downsample_dpi=self.settings["downsample dpi"],
            downsample=self.settings["downsample"],
            pdf_compression=self.settings["pdf compression"],
            text_position=self.settings["text_position"],
            can_encrypt_pdf="pdftk" in self._dependencies,
            tiff_compression=self.settings["tiff compression"],
        )

        # Frame for page range
        self._windowi.add_page_range()
        self._windowi.add_image_type()

        # Post-save hook
        pshbutton = Gtk.CheckButton(label=_("Post-save hook"))
        pshbutton.set_tooltip_text(
            _(
                "Run command on saved file. The available commands are those "
                "user-defined tools that do not specify %o"
            )
        )
        vbox = self._windowi.get_content_area()
        vbox.pack_start(pshbutton, False, True, 0)
        self._update_post_save_hooks()
        vbox.pack_start(self._windowi.comboboxpsh, False, True, 0)
        pshbutton.connect(
            "toggled",
            lambda _action: self._windowi.comboboxpsh.set_sensitive(
                pshbutton.get_active()
            ),
        )
        pshbutton.set_active(self.settings["post_save_hook"])
        self._windowi.comboboxpsh.set_sensitive(pshbutton.get_active())
        kbutton = Gtk.CheckButton(label=_("Close dialog on save"))
        kbutton.set_tooltip_text(_("Close dialog on save"))
        kbutton.set_active(self.settings["close_dialog_on_save"])
        vbox.pack_start(kbutton, False, True, 0)

        self._windowi.add_actions(
            [
                (
                    "gtk-save",
                    lambda: self._save_button_clicked_callback(kbutton, pshbutton),
                ),
                ("gtk-cancel", self._windowi.hide),
            ]
        )
        self._windowi.show_all()
        self._windowi.resize(1, 1)

    def _save_button_clicked_callback(self, kbutton, pshbutton):
        "Save selected pages"

        # Compile list of pages
        self.settings["Page range"] = self._windowi.page_range
        uuids = self._list_of_page_uuids()

        # dig out the image type, compression and quality
        self.settings["image type"] = self._windowi.image_type
        self.settings["close_dialog_on_save"] = kbutton.get_active()
        self.settings["post_save_hook"] = pshbutton.get_active()
        if (
            self.settings["post_save_hook"]
            and self._windowi.comboboxpsh.get_active() > EMPTY_LIST
        ):
            self.settings["current_psh"] = self._windowi.comboboxpsh.get_active_text()

        if re.search(r"pdf", self.settings["image type"]):
            if self.settings["image type"] == "pdf":  # not for pre/append or email
                self._windowi.update_config_dict(self.settings)

            # dig out the compression
            self.settings["downsample"] = self._windowi.downsample
            self.settings["downsample dpi"] = self._windowi.downsample_dpi
            self.settings["pdf compression"] = self._windowi.pdf_compression
            self.settings["quality"] = self._windowi.jpeg_quality
            self.settings["text_position"] = self._windowi.text_position
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "djvu":
            self._windowi.update_config_dict(self.settings)
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "tif":
            self.settings["tiff compression"] = self._windowi.tiff_compression
            self.settings["quality"] = self._windowi.jpeg_quality
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "txt":
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "hocr":
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "ps":
            self.settings["ps_backend"] = self._windowi.ps_backend
            logger.info("Selected '%s' as ps backend", self.settings["ps_backend"])
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "session":
            self._save_file_chooser(uuids)
        elif self.settings["image type"] == "jpg":
            self.settings["quality"] = self._windowi.jpeg_quality
            self._save_image(uuids)
        else:
            self._save_image(uuids)

    def _save_file_chooser(self, uuids):

        # cd back to cwd to save
        os.chdir(self.settings["cwd"])

        title = _("PDF filename")  # pdf, append, prepend
        filter_desc = _("PDF files")
        filter_list = ["pdf"]
        if self.settings["image type"] == "djvu":
            title = _("DjVu filename")
            filter_desc = _("DjVu files")
            filter_list = [self.settings["image type"]]
        elif self.settings["image type"] == "tif":
            title = _("TIFF filename")
            filter_desc = _("Image files")
            filter_list = [self.settings["image type"]]
        elif self.settings["image type"] == "txt":
            title = _("Text filename")
            filter_desc = _("Text files")
            filter_list = [self.settings["image type"]]
        elif self.settings["image type"] == "hocr":
            title = _("hOCR filename")
            filter_desc = _("hOCR files")
            filter_list = [self.settings["image type"]]
        elif self.settings["image type"] == "ps":
            title = _("PS filename")
            filter_desc = _("Postscript files")
            filter_list = [self.settings["image type"]]
        elif self.settings["image type"] == "session":
            title = _("gscan2pdf session filename")
            filter_desc = _("gscan2pdf session files")
            filter_list = ["gs2p"]
        file_chooser = Gtk.FileChooserDialog(
            title=title,
            parent=self._windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )
        if self.settings["image type"] in ["pdf", "djvu"]:
            filename = expand_metadata_pattern(
                template=self.settings["default filename"],
                convert_whitespace=self.settings["convert whitespace to underscores"],
                author=self.settings["author"],
                title=self.settings["title"],
                docdate=self._windowi.meta_datetime,
                today_and_now=datetime.datetime.now(),
                extension=self.settings["image type"],
                subject=self.settings["subject"],
                keywords=self.settings["keywords"],
            )
            file_chooser.set_current_name(filename)
            file_chooser.set_do_overwrite_confirmation(True)
        add_filter(file_chooser, filter_desc, filter_list)
        file_chooser.set_current_folder(self.settings["cwd"])
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.connect(
            "response",
            self._file_chooser_response_callback,
            [self.settings["image type"], uuids],
        )
        file_chooser.show()

        # cd back to tempdir
        os.chdir(self.session.name)

    def _list_of_page_uuids(self):
        "Compile list of pages"
        pagelist = self.slist.get_page_index(
            self.settings["Page range"], self._error_callback
        )
        if not pagelist:
            return []
        return [self.slist.data[i][2] for i in pagelist]

    def _file_chooser_response_callback(self, dialog, response, data):
        "Callback for file chooser dialog"
        filetype, uuids = data
        suffix = filetype
        if re.search(r"pdf", suffix, re.IGNORECASE):
            suffix = "pdf"
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            logger.debug("FileChooserDialog returned %s", filename)
            if not re.search(rf"[.]{suffix}$", filename, re.IGNORECASE):
                filename = f"{filename}.{filetype}"
                if file_exists(dialog, filename):
                    return

            if self._file_writable(dialog, filename):
                return

            # Update cwd
            self.settings["cwd"] = os.path.dirname(filename)
            if re.search(r"pdf", filetype, re.IGNORECASE):
                self._save_pdf(filename, uuids, filetype)

            elif filetype == "ps":
                if self.settings["ps_backend"] == "libtiff":
                    tif = tempfile.TemporaryFile(dir=self.session, suffix=".tif")
                    self._save_tif(tif.filename(), uuids, filename)
                else:
                    self._save_pdf(filename, uuids, "ps")

            elif filetype == "session":
                self.slist.save_session(filename, VERSION)

            elif filetype in ["djvu", "tif", "txt", "hocr"]:
                method = getattr(self, f"_save_{filetype}")
                method(filename, uuids)

            if self._windowi is not None and self.settings["close_dialog_on_save"]:
                self._windowi.hide()

        dialog.destroy()

    def _file_writable(self, chooser, filename):
        "Check if a file or its directory is writable and show an error dialog if not."

        if not os.access(
            os.path.dirname(filename), os.W_OK
        ):  # FIXME: replace with try/except
            text = _("Directory %s is read-only") % (os.path.dirname(filename))
            self._show_message_dialog(
                parent=chooser,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=text,
            )
            return True

        if os.path.isfile(filename) and not os.access(
            filename, os.W_OK
        ):  # FIXME: replace with try/except
            text = _("File %s is read-only") % (filename)
            self._show_message_dialog(
                parent=chooser,
                message_type="error",
                buttons=Gtk.ButtonsType.CLOSE,
                text=text,
            )
            return True

        return False

    def _save_pdf(self, filename, list_of_page_uuids, option):
        "Save selected pages as PDF under given name."

        # Compile options
        options = {
            "compression": self.settings["pdf compression"],
            "downsample": self.settings["downsample"],
            "downsample dpi": self.settings["downsample dpi"],
            "quality": self.settings["quality"],
            "text_position": self.settings["text_position"],
            "user-password": self._windowi.pdf_user_password,
            "set_timestamp": self.settings["set_timestamp"],
            "convert whitespace to underscores": self.settings[
                "convert whitespace to underscores"
            ],
        }
        if option == "prependpdf":
            options["prepend"] = filename

        elif option == "appendpdf":
            options["append"] = filename

        elif option == "ps":
            options["ps"] = filename
            options["pstool"] = self.settings["ps_backend"]

        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        # Create the PDF
        logger.debug("Started saving %s", filename)

        def save_pdf_finished_callback(response):
            self.post_process_progress.finish(response)
            self.slist.thread.send("set_saved", list_of_page_uuids)
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                if "ps" in options:
                    launch_default_for_file(options["ps"])
                else:
                    launch_default_for_file(filename)

            logger.debug("Finished saving %s", filename)

        self.slist.save_pdf(
            path=filename,
            list_of_pages=list_of_page_uuids,
            metadata=collate_metadata(self.settings, datetime.datetime.now()),
            options=options,
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_pdf_finished_callback,
            error_callback=self._error_callback,
        )

    def _save_djvu(self, filename, uuids):
        "Save a list of pages as a DjVu file."

        # cd back to tempdir
        os.chdir(self.session.name)

        # Create the DjVu
        logger.debug("Started saving %s", filename)
        options = {
            "set_timestamp": self.settings["set_timestamp"],
            "convert whitespace to underscores": self.settings[
                "convert whitespace to underscores"
            ],
        }
        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        def save_djvu_finished_callback(response):
            filename = response.request.args[0]["path"]
            self.post_process_progress.finish(response)
            self.slist.thread.send("set_saved", uuids)
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                launch_default_for_file(filename)
            logger.debug("Finished saving %s", filename)

        self.slist.save_djvu(
            path=filename,
            list_of_pages=uuids,
            options=options,
            metadata=collate_metadata(self.settings, datetime.datetime.now()),
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_djvu_finished_callback,
            error_callback=self._error_callback,
        )

    def _save_tif(self, filename, uuids, ps=None):
        "Save a list of pages as a TIFF file with specified options"
        options = {
            "compression": self.settings["tiff compression"],
            "quality": self.settings["quality"],
            "ps": ps,
        }
        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        def save_tiff_finished_callback(response):
            filename = response.request.args[0]["path"]
            self.post_process_progress.finish(response)
            self.slist.thread.send("set_saved", uuids)
            file = ps if ps is not None else filename
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                launch_default_for_file(file)

            logger.debug("Finished saving %s", file)

        self.slist.save_tiff(
            path=filename,
            list_of_pages=uuids,
            options=options,
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_tiff_finished_callback,
            error_callback=self._error_callback,
        )

    def _save_txt(self, filename, uuids):
        "Save OCR text"
        options = {}
        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        def save_text_finished_callback(response):
            self.post_process_progress.finish(response)
            self.slist.thread.send("set_saved", uuids)
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                launch_default_for_file(filename)

            logger.debug("Finished saving %s", filename)

        self.slist.save_text(
            path=filename,
            list_of_pages=uuids,
            options=options,
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_text_finished_callback,
            error_callback=self._error_callback,
        )

    def _save_hocr(self, filename, uuids):
        "Save HOCR (HTML OCR) data to a file"
        options = {}
        if self.settings["post_save_hook"]:
            options["post_save_hook"] = self.settings["current_psh"]

        def save_hocr_finished_callback(response):
            self.slist.thread.send("set_saved", uuids)
            self.post_process_progress.finish(response)
            if (
                "view files toggle" in self.settings
                and self.settings["view files toggle"]
            ):
                launch_default_for_file(filename)

            logger.debug("Finished saving %s", filename)

        self.slist.save_hocr(
            path=filename,
            list_of_pages=uuids,
            options=options,
            queued_callback=self.post_process_progress.queued,
            started_callback=self.post_process_progress.update,
            running_callback=self.post_process_progress.update,
            finished_callback=save_hocr_finished_callback,
            error_callback=self._error_callback,
        )

    def _save_image(self, uuids):
        "Save selected pages as image under given name."

        # cd back to cwd to save
        os.chdir(self.settings["cwd"])

        # Set up file selector
        file_chooser = Gtk.FileChooserDialog(
            title=_("Image filename"),
            parent=self._windowi,
            action=Gtk.FileChooserAction.SAVE,
        )
        file_chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        file_chooser.set_default_response(Gtk.ResponseType.OK)
        file_chooser.set_current_folder(self.settings["cwd"])
        add_filter(
            file_chooser,
            _("Image files"),
            ["jpg", "png", "pnm", "gif", "tif", "tiff", "pdf", "djvu", "ps"],
        )
        file_chooser.set_do_overwrite_confirmation(True)
        if file_chooser.run() == Gtk.ResponseType.OK:
            filename = file_chooser.get_filename()

            # Update cwd
            self.settings["cwd"] = os.path.dirname(filename)

            # cd back to tempdir
            os.chdir(self.session.name)
            if len(uuids) > 1:
                w = len(uuids)
                for i in range(1, len(uuids) + 1):
                    current_filename = (
                        f"{filename}_%0{w}d.{self.settings['image type']}" % (i)
                    )
                    if os.path.isfile(current_filename):
                        text = _("This operation would overwrite %s") % (
                            current_filename
                        )
                        self._show_message_dialog(
                            parent=file_chooser,
                            message_type="error",
                            buttons=Gtk.ButtonsType.CLOSE,
                            text=text,
                        )
                        file_chooser.destroy()
                        return

                filename = f"${filename}_%0${w}d.{self.settings['image type']}"

            else:
                if not re.search(
                    rf"[.]{self.settings['image type']}$",
                    filename,
                    re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE,
                ):
                    filename = f"{filename}.{self.settings['image type']}"
                    if file_exists(file_chooser, filename):
                        return

                if self._file_writable(file_chooser, filename):
                    return

            # Create the image
            logger.debug("Started saving %s", filename)

            def save_image_finished_callback(response):
                filename = response.request.args[0]["path"]
                self.post_process_progress.finish(response)
                self.slist.thread.send("set_saved", uuids)
                if (
                    "view files toggle" in self.settings
                    and self.settings["view files toggle"]
                ):
                    w = len(uuids)
                    if w > 1:
                        for i in range(1, w + 1):
                            launch_default_for_file(filename % (i))
                    else:
                        launch_default_for_file(filename)

                logger.debug("Finished saving %s", filename)

            self.slist.save_image(
                path=filename,
                list_of_pages=uuids,
                queued_callback=self.post_process_progress.queued,
                started_callback=self.post_process_progress.update,
                running_callback=self.post_process_progress.update,
                finished_callback=save_image_finished_callback,
                error_callback=self._error_callback,
            )
            if self._windowi is not None:
                self._windowi.hide()

        file_chooser.destroy()

    def _update_post_save_hooks(self):
        "Updates the post-save hooks"
        if self._windowi is not None:
            if hasattr(self._windowi, "comboboxpsh"):

                # empty combobox
                for _i in range(1, self._windowi.comboboxpsh.get_num_rows() + 1):
                    self._windowi.comboboxpsh.remove(0)

            else:
                # create it
                self._windowi.comboboxpsh = ComboBoxText()

            # fill it again
            for tool in self.settings["user_defined_tools"]:
                if not re.search(r"%o", tool, re.MULTILINE | re.DOTALL | re.VERBOSE):
                    self._windowi.comboboxpsh.append_text(tool)

            self._windowi.comboboxpsh.set_active_by_text(self.settings["current_psh"])

    def print_dialog(self, _action, _param):
        "print"
        os.chdir(self.settings["cwd"])
        print_op = PrintOperation(settings=self.print_settings, slist=self.slist)
        res = print_op.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
        if res == Gtk.PrintOperationResult.APPLY:
            self.print_settings = print_op.get_print_settings()
        os.chdir(self.session.name)

    def quit_app(self, _action, _param):
        "Handle the quit action for the application."
        if self._can_quit():
            self.get_application().quit()

    def _can_quit(self):
        "Remove temporary files, note window state, save settings and quit."
        if not self._pages_saved(
            _("Some pages have not been saved.\nDo you really want to quit?")
        ):
            return False

        # Make sure that we are back in the start directory,
        # otherwise we can't delete the temp dir.
        os.chdir(self.settings["cwd"])

        # Remove temporary files
        for file in glob.glob(self.session.name + "/*"):
            os.remove(file)
        os.rmdir(self.session.name)
        # Write window state to settings
        self.settings["window_width"], self.settings["window_height"] = self.get_size()
        self.settings["window_x"], self.settings["window_y"] = self.get_position()
        self.settings["thumb panel"] = self._hpaned.get_position()
        if self._windows:
            (
                self.settings["scan_window_width"],
                self.settings["scan_window_height"],
            ) = self._windows.get_size()
            logger.info("Killing Sane thread(s)")
            self._windows.thread.quit()

        # Write config file
        config.write_config(self._configfile, self.settings)
        logger.info("Killing document thread(s)")
        self.slist.thread.quit()
        logger.debug("Quitting")

        # remove lock
        fcntl.lockf(self._lockfd, fcntl.LOCK_UN)

        return True

    def _restart(self):
        "Restart the application"
        self._can_quit()
        os.execv(sys.executable, ["python"] + sys.argv)

    def _pages_saved(self, message):
        "Check that all pages have been saved"
        if not self.slist.thread.pages_saved():
            response = self._ask_question(
                parent=self,
                type="question",
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=message,
                store_response=True,
                stored_responses=[Gtk.ResponseType.OK],
            )
            if response != Gtk.ResponseType.OK:
                return False
        return True
