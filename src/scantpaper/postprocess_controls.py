"""provide postprocessing rotate controls for the scan dialog."""

from __future__ import annotations

from typing import cast

import gi

from scantpaper.comboboxtext import ComboBoxText
from scantpaper.const import PERCENT
from scantpaper.gobject import property_
from scantpaper.i18n import _
from scantpaper.tesseract import (
    ENGINE_MODE_DEFAULT,
    code2name,
    engine_modes,
    get_tesseract_codes,
    get_tesseract_variables,
    join_language_spec,
    languages,
    page_segmentation_modes,
    parse_variables,
    split_language_spec,
    validate_file_variables,
    validate_language_spec,
    validate_variable_names,
)

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    GObject,
    Gtk,
)

SIDE = [
    ["both", _("Both sides"), _("Both sides.")],
    ["facing", _("Facing side"), _("Facing side.")],
    ["reverse", _("Reverse side"), _("Reverse side.")],
]
ROTATE = [
    [90, _("90°"), _("Rotate image 90 degrees clockwise.")],
    [180, _("180°"), _("Rotate image 180 degrees clockwise.")],
    [270, _("270°"), _("Rotate image 90 degrees anticlockwise.")],
]

# Engine variables set through a dedicated control, with that control's label.
MANAGED_VARIABLES = {
    "tessedit_pageseg_mode": _("Page segmentation mode"),
    "tessedit_ocr_engine_mode": _("OCR engine mode"),
}


class RotateControlRow(Gtk.Box):
    """provide a row of postprocessing rotate controls for the scan dialog."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise RotateControlRow."""
        super().__init__(*args, **kwargs)
        self.cbutton = Gtk.CheckButton(label=_("Rotate"))
        self.cbutton.set_tooltip_text(_("Rotate image after scanning"))
        self.append(self.cbutton)
        self.cbutton.set_hexpand(True)
        self.side_cmbx = ComboBoxText(data=SIDE)
        self.side_cmbx.set_tooltip_text(_("Select side to rotate"))
        self.append(self.side_cmbx)
        self.side_cmbx.set_hexpand(True)
        self.angle_cmbx = ComboBoxText(data=ROTATE)
        self.angle_cmbx.set_tooltip_text(_("Select angle of rotation"))
        self.append(self.angle_cmbx)
        self.angle_cmbx.set_hexpand(True)
        self.append(Gtk.Label(label=_("Anticlockwise")))


class RotateControls(Gtk.Box):
    """provide postprocessing rotate controls for the scan dialog."""

    _recomputing = False
    _rotate_facing = 0

    @property_(
        type=int,
        nick="Rotate facing",
        blurb="Angle to rotate facing side",
    )
    def rotate_facing(self) -> int:
        """Getter for rotate_facing attribute."""
        return self._rotate_facing

    @rotate_facing.setter
    def rotate_facing(self, newval: int) -> None:
        if newval == self._rotate_facing:
            return
        self._rotate_facing = newval
        self._update_gui()

    _rotate_reverse = 0

    @property_(
        type=int,
        nick="Rotate reverse",
        blurb="Angle to rotate reverse side",
    )
    def rotate_reverse(self) -> int:
        """Getter for rotate_reverse attribute."""
        return self._rotate_reverse

    @rotate_reverse.setter
    def rotate_reverse(self, newval: int) -> None:
        if newval == self._rotate_reverse:
            return
        self._rotate_reverse = newval
        self._update_gui()

    _can_duplex = True

    @property_(
        type=bool,
        default=True,
        nick="Can duplex",
        blurb="Scanner capable of duplex scanning",
    )
    def can_duplex(self) -> bool:
        """Getter for can_duplex attribute."""
        return self._can_duplex

    @can_duplex.setter
    def can_duplex(self, newval: bool) -> None:
        if newval == self._can_duplex:
            return
        self._can_duplex = newval
        if newval:
            self._side1.side_cmbx.show()
            self._side2.side_cmbx.show()
        else:
            self._side1.side_cmbx.hide()
            self._side2.side_cmbx.hide()

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise ."""
        # have to do this manually, since Gtk.Box messes with the initialization
        rotate_facing = kwargs.pop("rotate_facing", kwargs.pop("rotate-facing", 0))
        rotate_reverse = kwargs.pop("rotate_reverse", kwargs.pop("rotate-reverse", 0))
        can_duplex = kwargs.pop("can_duplex", kwargs.pop("can-duplex", True))

        super().__init__(*args, **kwargs)
        self.set_orientation(orientation=Gtk.Orientation.VERTICAL)
        self._side1 = RotateControlRow()
        self.append(self._side1)
        self._side1.set_vexpand(True)
        self._side2 = RotateControlRow()
        self.append(self._side2)
        self._side1.cbutton.connect("toggled", self._toggled_rotate_callback)
        self._side2.cbutton.connect("toggled", self._update_attributes)
        self._side1.side_cmbx.connect("changed", self._toggled_rotate_side_callback)
        self._side2.side_cmbx.connect("changed", self._update_attributes)
        self._side1.angle_cmbx.connect("changed", self._update_attributes)
        self._side2.angle_cmbx.connect("changed", self._update_attributes)

        # have to do this manually, since Gtk.Box messes with the initialization
        self.rotate_facing = rotate_facing
        self.rotate_reverse = rotate_reverse
        self.can_duplex = can_duplex

        # In case it isn't set elsewhere
        if self.rotate_facing == 0 and self.rotate_reverse == 0:
            self._side1.side_cmbx.set_active_index("both")
            self._side1.angle_cmbx.set_active_index(90)

        # Sync GUI with properties set during instantiation
        self._update_gui()

    def _toggled_rotate_callback(self, _widget: Gtk.Widget) -> None:
        self._update_attributes(None)

    def _toggled_rotate_side_callback(self, _widget: Gtk.Widget) -> None:
        self._update_attributes(None)

    def _update_side2_options(self) -> None:
        side1_cmbx_i = self._side1.side_cmbx.get_active()
        angle1_cmbx_i = self._side1.angle_cmbx.get_active()

        # Empty combobox
        while self._side2.side_cmbx.get_num_rows() > 0:
            self._side2.side_cmbx.remove(0)

        side2 = [s for s in SIDE if s[0] not in ["both", SIDE[side1_cmbx_i][0]]]
        for s in side2:
            self._side2.side_cmbx.append_text(s[1])
        self._side2.side_cmbx.data = side2
        self._side2.side_cmbx.set_active(0)

        # Empty combobox
        while self._side2.angle_cmbx.get_num_rows() > 0:
            self._side2.angle_cmbx.remove(0)

        angle2 = []
        for a in ROTATE:
            if angle1_cmbx_i != -1 and a[0] != ROTATE[angle1_cmbx_i][0]:
                angle2.append(a)
                self._side2.angle_cmbx.append_text(a[1])
        self._side2.angle_cmbx.data = angle2
        self._side2.angle_cmbx.set_active(0)

    def _update_attributes(self, _widget: object) -> None:
        if self._recomputing:
            return
        self._recomputing = True

        rotate_facing = 0
        rotate_reverse = 0
        if self._side1.cbutton.get_active():
            side1 = self._side1.side_cmbx.get_active_index()
            angle1 = self._side1.angle_cmbx.get_active_index()
            if side1 == "both":
                rotate_facing = angle1
                rotate_reverse = rotate_facing
            elif side1 == "facing":
                rotate_facing = angle1
            else:
                rotate_reverse = angle1

            if self._side2.cbutton.get_active():
                side2 = self._side2.side_cmbx.get_active_index()
                angle2 = self._side2.angle_cmbx.get_active_index()
                if side2 == "facing":
                    rotate_facing = angle2
                else:
                    rotate_reverse = angle2

        self.rotate_facing = rotate_facing
        self.rotate_reverse = rotate_reverse
        self._recomputing = False

    def _update_gui(self) -> None:
        self._recomputing = True
        if self.rotate_facing == 0 and self.rotate_reverse == 0:
            self._side1.cbutton.set_active(False)
            self._side2.set_sensitive(False)
            self._side2.cbutton.set_active(False)
        else:
            self._side1.cbutton.set_active(True)
            if self.rotate_facing == self.rotate_reverse:
                self._side1.side_cmbx.set_active_index("both")
                self._side1.angle_cmbx.set_active_index(self.rotate_facing)
                self._side2.set_sensitive(False)
                self._side2.cbutton.set_active(False)
            elif self.rotate_facing != 0 and self.rotate_reverse != 0:
                self._side1.side_cmbx.set_active_index("facing")
                self._side1.angle_cmbx.set_active_index(self.rotate_facing)
                self._side2.set_sensitive(True)
                self._side2.cbutton.set_active(True)
                self._update_side2_options()
                self._side2.side_cmbx.set_active_index("reverse")
                self._side2.angle_cmbx.set_active_index(self.rotate_reverse)
            elif self.rotate_facing != 0:
                self._side1.side_cmbx.set_active_index("facing")
                self._side1.angle_cmbx.set_active_index(self.rotate_facing)
                self._side2.set_sensitive(True)
                self._side2.cbutton.set_active(False)
                self._update_side2_options()
            else:  # self.rotate_reverse != 0
                self._side1.side_cmbx.set_active_index("reverse")
                self._side1.angle_cmbx.set_active_index(self.rotate_reverse)
                self._side2.set_sensitive(True)
                self._side2.cbutton.set_active(False)
                self._update_side2_options()

        self._recomputing = False


class OCRControls(Gtk.Box):
    """Provides post-processing OCR options for the scan dialog."""

    available_engines = GObject.Property(
        type=object,
        nick="OCR engines",
        blurb="List of available OCR engines",
    )
    _engine = None

    @property_(
        type=str,
        default=None,
        nick="OCR engine",
        blurb="Currently selected OCR engine",
    )
    def engine(self) -> str | None:
        """Getter for engine attribute."""
        return cast("str | None", (self._engine))

    @engine.setter
    def engine(self, newval: str | None) -> None:
        self._engine = newval

    _language = None

    @property_(
        type=str,
        default=None,
        nick="OCR language",
        blurb="Currently selected OCR language",
    )
    def language(self) -> str | None:
        """Getter for language attribute."""
        return cast("str | None", (self._language))

    @language.setter
    def language(self, newval: str | None) -> None:
        self._language = newval
        if hasattr(self, "_options_box"):
            self._load_language()

    _variables = ""

    @property
    def variables(self) -> str:
        """Getter for additional tesseract variables."""
        if hasattr(self, "_variables_view"):
            buffer = self._variables_view.get_buffer()
            return cast(
                "str",
                buffer.get_text(
                    buffer.get_start_iter(),
                    buffer.get_end_iter(),
                    include_hidden_chars=True,
                ),
            )
        return self._variables

    @variables.setter
    def variables(self, newval: str | None) -> None:
        self._variables = "" if newval is None else newval
        if hasattr(self, "_variables_view"):
            self._variables_view.get_buffer().set_text(self._variables)

    _psm: object = ""

    @property
    def psm(self) -> object:
        """Getter for the page segmentation mode."""
        if hasattr(self, "_psm_cmbx"):
            return self._psm_cmbx.get_active_index()
        return self._psm

    @psm.setter
    def psm(self, newval: object) -> None:
        self._psm = newval
        if hasattr(self, "_psm_cmbx"):
            self._set_combo_index(self._psm_cmbx, newval)

    _engine_mode = ENGINE_MODE_DEFAULT

    @property
    def engine_mode(self) -> str:
        """Getter for the OCR engine mode."""
        if hasattr(self, "_engine_mode_cmbx"):
            return cast("str", self._engine_mode_cmbx.get_active_index())
        return self._engine_mode

    @engine_mode.setter
    def engine_mode(self, newval: object) -> None:
        self._engine_mode = ENGINE_MODE_DEFAULT if newval is None else str(newval)
        if hasattr(self, "_engine_mode_cmbx"):
            self._set_combo_index(self._engine_mode_cmbx, self._engine_mode)

    @staticmethod
    def _set_combo_index(cmbx: ComboBoxText, value: object) -> None:
        """Select the row whose index value matches, else the first row."""
        for i, row in enumerate(cmbx.data):
            if row[0] == value:
                cmbx.set_active(i)
                return
        cmbx.set_active(0)

    _active = False

    @property_(
        type=bool,
        default=False,
        nick="Active",
        blurb="Whether OCR will be automatically performed",
    )
    def active(self) -> bool:
        """Getter for active attribute."""
        return self._active

    @active.setter
    def active(self, newval: bool) -> None:
        self._active = newval
        if hasattr(self, "_active_button"):
            self._active_button.set_active(newval)

    _threshold = False

    @property_(
        type=bool,
        default=False,
        nick="Threshold",
        blurb="Whether to threshold before performing OCR",
    )
    def threshold(self) -> bool:
        """Getter for threshold attribute."""
        return self._threshold

    @threshold.setter
    def threshold(self, newval: bool) -> None:
        self._threshold = newval
        if hasattr(self, "_threshold_button"):
            self._threshold_button.set_active(newval)

    _threshold_value = 20.0

    @property_(
        type=float,
        default=20.0,
        nick="Threshold value",
        blurb="Pixels that differ from the paper colour by more than this "
        "percentage are rendered black",
    )
    def threshold_value(self) -> float:
        """Getter for threshold_value attribute."""
        return self._threshold_value

    @threshold_value.setter
    def threshold_value(self, newval: float) -> None:
        self._threshold_value = newval
        if hasattr(self, "_threshold_spin"):
            self._threshold_spin.set_value(newval)

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise ."""
        variables = kwargs.pop("variables", "")
        psm = kwargs.pop("psm", "")
        engine_mode = kwargs.pop("engine_mode", ENGINE_MODE_DEFAULT)
        super().__init__(*args, **kwargs)
        self._variables = "" if variables is None else str(variables)
        self.psm = psm
        self.engine_mode = engine_mode
        self._syncing = False
        self._primary_language: str | None = None
        self._additional_languages: list[str] = []
        self._tesscodes: list[str] = []
        self._langs: dict[str, str] = {}
        self._additional_checks: dict[str, Gtk.CheckButton] = {}
        self.set_orientation(orientation=Gtk.Orientation.VERTICAL)
        hboxo = Gtk.Box()
        self.append(hboxo)
        self._active_button = Gtk.CheckButton(label=_("OCR scanned pages"))
        self._active_button.set_tooltip_text(_("OCR scanned pages"))

        tesseract = False
        for engine in list(self.available_engines or []):
            if engine[0] == "tesseract":
                tesseract = True

        if not tesseract:
            hboxo.set_sensitive(False)
            self._active_button.set_active(False)
        elif self.active:
            self._active_button.set_active(self.active)

        hboxo.append(self._active_button)
        self._active_button.set_hexpand(True)
        hboxtl = None

        if tesseract:
            hboxtl = self._add_tess_language_controls()

            if not self._active_button.get_active():
                hboxtl.set_sensitive(False)

            self._active_button.connect("toggled", self.on_toggled_active, hboxtl)

        # Checkbox & SpinButton for threshold
        hboxt = Gtk.Box()
        self.append(hboxt)
        self._threshold_button = Gtk.CheckButton(label=_("Threshold before OCR"))
        self._threshold_button.set_tooltip_text(
            _(
                "Threshold the image before performing OCR. "
                "This only affects the image passed to the OCR engine, and not the image stored."
            )
        )
        self._threshold_button.set_active(self.threshold)
        hboxt.append(self._threshold_button)
        labelp = Gtk.Label(label=PERCENT)
        self._threshold_spin = Gtk.SpinButton.new_with_range(0, 100, 1)
        self._threshold_spin.set_tooltip_text(
            _(
                "Pixels that differ from the paper colour by more than this "
                "percentage are rendered black. Higher values only keep "
                "stronger marks."
            )
        )
        self._threshold_spin.set_value(self.threshold_value)
        self._threshold_spin.set_sensitive(self.threshold)
        hboxt.append(self._threshold_spin)
        hboxt.append(labelp)
        self._threshold_button.connect(
            "toggled", self.on_toggled_threshold, self._threshold_spin
        )
        self._threshold_spin.connect("value-changed", self.on_threshold_changed)

    def on_toggled_active(self, checkbox: Gtk.CheckButton, hboxtl: Gtk.Box) -> None:
        """React to OCR active checkbox toggle."""
        self.active = checkbox.get_active()
        hboxtl.set_sensitive(sensitive=self.active)

    def on_toggled_threshold(
        self, checkbox: Gtk.CheckButton, spinbutton: Gtk.SpinButton
    ) -> None:
        """React to threshold checkbox toggle."""
        self.threshold = checkbox.get_active()
        spinbutton.set_sensitive(sensitive=self.threshold)

    def on_threshold_changed(self, _widget: Gtk.SpinButton, value: float) -> None:
        """React to threshold value spinbutton change."""
        self.threshold_value = value

    def on_language_changed(self, widget: ComboBoxText) -> None:
        """React to OCR language combobox change."""
        if self._syncing:
            return
        primary = widget.get_active_index()
        if primary is None or primary == self._primary_language:
            return
        self._primary_language = cast("str", primary)
        if self._primary_language in self._additional_languages:
            self._additional_languages.remove(self._primary_language)
        self._syncing = True
        try:
            self._rebuild_additional_languages()
        finally:
            self._syncing = False
        self._update_language_from_controls()

    @property
    def validation_error(self) -> str | None:
        """Return a user-facing error for the current OCR options."""
        if self.language is None or self.language == "":
            return _("No OCR language selected.")
        missing = validate_language_spec(self.language, self._tesscodes)
        if missing:
            return _("The following OCR languages are not installed: %(languages)s") % {
                "languages": ", ".join(missing)
            }
        try:
            variables = parse_variables(self.variables)
        except ValueError as exc:
            return str(exc)
        for name, control in MANAGED_VARIABLES.items():
            if name in variables:
                return _(
                    "'%(variable)s' is set by the %(control)s control; "
                    "remove it from this field."
                ) % {"variable": name, "control": control}
        error = validate_file_variables(variables)
        if error is None:
            unknown = validate_variable_names(variables, get_tesseract_variables())
            if len(unknown) == 1:
                error = _("Unknown Tesseract option: %(variable)s") % {
                    "variable": unknown[0]
                }
            elif unknown:
                error = _("Unknown Tesseract options: %(variables)s") % {
                    "variables": ", ".join(unknown)
                }
        return error

    def _add_tess_language_controls(self) -> Gtk.Box:
        self._options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self._options_box)
        self._tesscodes = get_tesseract_codes()
        self._langs = languages(self._tesscodes)

        hbox = Gtk.Box()
        self._options_box.append(hbox)
        hbox.append(Gtk.Label(label=_("Language to recognise")))

        self._primary_cmbx = ComboBoxText()
        self._primary_cmbx.connect("changed", self.on_language_changed)
        hbox.append(self._primary_cmbx)

        hbox2 = Gtk.Box()
        self._options_box.append(hbox2)
        hbox2.append(Gtk.Label(label=_("Additional languages")))

        self._additional_popover = Gtk.Popover()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_width(250)
        scrolled.set_min_content_height(200)
        self._additional_listbox = Gtk.ListBox()
        scrolled.set_child(self._additional_listbox)
        self._additional_popover.set_child(scrolled)
        self._additional_button = Gtk.MenuButton()
        self._additional_button.set_popover(self._additional_popover)
        self._additional_button.set_label(_("None"))
        hbox2.append(self._additional_button)

        self._load_language()
        self._add_mode_controls()
        self._add_advanced_options()
        return self._options_box

    def _add_mode_controls(self) -> None:
        psm_box = Gtk.Box()
        self._options_box.append(psm_box)
        psm_box.append(Gtk.Label(label=_("Page segmentation mode")))
        self._psm_cmbx = ComboBoxText(data=page_segmentation_modes)
        self._psm_cmbx.set_tooltip_text(
            _("How tesseract should segment the page. Automatic suits most pages.")
        )
        psm_box.append(self._psm_cmbx)

        mode_box = Gtk.Box()
        self._options_box.append(mode_box)
        mode_box.append(Gtk.Label(label=_("OCR engine mode")))
        self._engine_mode_cmbx = ComboBoxText(data=engine_modes)
        self._engine_mode_cmbx.set_tooltip_text(
            _("Which tesseract engine to use. Default uses the engine's own choice.")
        )
        mode_box.append(self._engine_mode_cmbx)

        self.psm = self._psm
        self.engine_mode = self._engine_mode

    def _add_advanced_options(self) -> None:
        expander = Gtk.Expander(label=_("Advanced Tesseract engine parameters"))
        expander.set_tooltip_text(
            _(
                "Tesseract engine parameters - the values of tesseract's -c "
                "option - not command-line flags. Use absolute paths."
            )
        )
        self._advanced_expander = expander
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hint = Gtk.Label(
            label=_(
                "One name=value engine parameter per line, e.g. "
                "user_words_file=/path/to/words.txt. Write engine parameters, "
                "not command-line options such as --user-words."
            )
        )
        hint.set_wrap(True)
        hint.set_xalign(0)
        self._advanced_hint = hint
        vbox.append(hint)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(70)
        self._variables_view = Gtk.TextView()
        self._variables_view.set_monospace(True)
        self._variables_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._variables_view.get_buffer().set_text(self._variables)
        scrolled.set_child(self._variables_view)
        vbox.append(scrolled)
        expander.set_child(vbox)
        self._options_box.append(expander)

    def _load_language(self) -> None:
        codes = split_language_spec(self._language)
        if codes:
            self._primary_language = codes[0]
            self._additional_languages = codes[1:]
        else:
            installed = sorted(self._tesscodes)
            self._primary_language = installed[0] if installed else None
            self._additional_languages = []
            if self._primary_language is not None:
                self._language = self._primary_language
        self._syncing = True
        try:
            self._rebuild_primary_combo()
            self._rebuild_additional_languages()
        finally:
            self._syncing = False
        self._update_additional_button_label()

    def _rebuild_primary_combo(self) -> None:
        rows: list[list[object]] = [
            [code, self._language_name(code)] for code in sorted(self._tesscodes)
        ]
        known = {row[0] for row in rows}
        for code in split_language_spec(self._language):
            if code not in known:
                rows.append([code, self._language_label(code)])
                known.add(code)
        self._primary_cmbx.remove_all()
        self._primary_cmbx.data = rows
        for _code, label in rows:
            self._primary_cmbx.append_text(label)
        self._primary_cmbx.set_active_index(self._primary_language)

    def _rebuild_additional_languages(self) -> None:
        while child := self._additional_listbox.get_first_child():
            self._additional_listbox.remove(child)
        self._additional_checks = {}
        codes = [
            code for code in sorted(self._tesscodes) if code != self._primary_language
        ]
        known = set(codes)
        if self._primary_language is not None:
            known.add(self._primary_language)
        for code in self._additional_languages:
            if code not in known:
                codes.append(code)
                known.add(code)
        for code in codes:
            check = Gtk.CheckButton(label=self._language_label(code))
            check.set_active(code in self._additional_languages)
            check.connect("toggled", self._on_additional_language_toggled, code)
            self._additional_listbox.append(check)
            self._additional_checks[code] = check

    def _on_additional_language_toggled(
        self, checkbox: Gtk.CheckButton, code: str
    ) -> None:
        if self._syncing:
            return
        if checkbox.get_active():
            if (
                code != self._primary_language
                and code not in self._additional_languages
            ):
                self._additional_languages.append(code)
        elif code in self._additional_languages:
            self._additional_languages.remove(code)
        self._update_language_from_controls()

    def _update_language_from_controls(self) -> None:
        spec = join_language_spec(self._primary_language, self._additional_languages)
        self._language = spec or None
        self._update_additional_button_label()

    def _update_additional_button_label(self) -> None:
        if not self._additional_languages:
            self._additional_button.set_label(_("None"))
            self._additional_button.set_tooltip_text(_("No additional languages"))
            return
        label = ", ".join(
            self._language_label(code) for code in self._additional_languages
        )
        self._additional_button.set_label(label)
        self._additional_button.set_tooltip_text(label)

    def _language_name(self, code: str) -> str:
        return cast("str", self._langs.get(code, code2name(code)))

    def _language_label(self, code: str) -> str:
        name = self._language_name(code)
        if code in self._tesscodes:
            return name
        return _("%(language)s (not installed)") % {"language": name}
