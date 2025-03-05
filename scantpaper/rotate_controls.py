"provide postprocessing rotate controls for the scan dialog"
import gi
from comboboxtext import ComboBoxText
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position

SIDE = [
    ["both", _("Both sides"), _("Both sides.")],
    ["facing", _("Facing side"), _("Facing side.")],
    ["reverse", _("Reverse side"), _("Reverse side.")],
]
ROTATE = [
    [90, _("90"), _("Rotate image 90 degrees clockwise.")],
    [180, _("180"), _("Rotate image 180 degrees clockwise.")],
    [270, _("270"), _("Rotate image 90 degrees anticlockwise.")],
]


class RotateControlRow(Gtk.HBox):
    "provide a row of postprocessing rotate controls for the scan dialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cbutton = Gtk.CheckButton(label=_("Rotate"))
        self.cbutton.set_tooltip_text(_("Rotate image after scanning"))
        self.pack_start(self.cbutton, True, True, 0)
        self.side_cmbx = ComboBoxText(data=SIDE)
        self.side_cmbx.set_tooltip_text(_("Select side to rotate"))
        self.pack_start(self.side_cmbx, True, True, 0)
        self.angle_cmbx = ComboBoxText(data=ROTATE)
        self.angle_cmbx.set_tooltip_text(_("Select angle of rotation"))
        self.pack_end(self.angle_cmbx, True, True, 0)


class RotateControls(Gtk.VBox):
    "provide postprocessing rotate controls for the scan dialog"
    _rotate_facing = 0

    @GObject.Property(
        type=int,
        nick="Rotate facing",
        blurb="Angle to rotate facing side",
    )
    def rotate_facing(self):  # pylint: disable=method-hidden
        "getter for rotate_facing attribute"
        return self._rotate_facing

    @rotate_facing.setter
    def rotate_facing(self, newval):
        if newval == self._rotate_facing:
            return
        self._rotate_facing = newval
        self._update_gui()

    _rotate_reverse = 0

    @GObject.Property(
        type=int,
        nick="Rotate reverse",
        blurb="Angle to rotate reverse side",
    )
    def rotate_reverse(self):  # pylint: disable=method-hidden
        "getter for rotate_reverse attribute"
        return self._rotate_reverse

    @rotate_reverse.setter
    def rotate_reverse(self, newval):
        if newval == self._rotate_reverse:
            return
        self._rotate_reverse = newval
        self._update_gui()

    _can_duplex = True

    @GObject.Property(
        type=bool,
        default=True,
        nick="Can duplex",
        blurb="Scanner capable of duplex scanning",
    )
    def can_duplex(self):  # pylint: disable=method-hidden
        "getter for can_duplex attribute"
        return self._can_duplex

    @can_duplex.setter
    def can_duplex(self, newval):
        if newval == self._can_duplex:
            return
        self._can_duplex = newval
        if newval:
            self._side1.side_cmbx.show()
            self._side2.side_cmbx.show()
        else:
            self._side1.side_cmbx.hide()
            self._side2.side_cmbx.hide()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._side1 = RotateControlRow()
        self.pack_start(self._side1, True, True, 0)
        self._side2 = RotateControlRow()
        self.pack_start(self._side2, False, False, 0)
        self._side1.cbutton.connect("toggled", self._toggled_rotate_callback)
        self._side1.side_cmbx.connect("changed", self._toggled_rotate_side_callback)

        # In case it isn't set elsewhere
        self._side2.side_cmbx.set_active_index(90)
        self._update_gui()

    def _toggled_rotate_callback(self, _widget):
        if self._side1.cbutton.get_active():
            if SIDE[self._side1.side_cmbx.get_active()][0] != "both":
                self._side2.set_sensitive(True)
        else:
            self._side2.set_sensitive(False)

    def _toggled_rotate_side_callback(self, side1_cmbx):
        side1_cmbx_i = side1_cmbx.get_active()
        if SIDE[side1_cmbx_i][0] == "both":
            self._side2.set_sensitive(False)
            self._side2.cbutton.set_active(False)
        else:
            if self._side1.cbutton.get_active():
                self._side2.set_sensitive(True)

            # Empty combobox
            while self._side2.side_cmbx.get_num_rows() > 0:
                self._side2.side_cmbx.remove(0)
                self._side2.side_cmbx.set_active(0)

            side2 = []
            for s in SIDE:
                if s[0] not in ["both", SIDE[side1_cmbx_i][0]]:
                    side2.append(s)
            self._side2.side_cmbx.append_text(side2[0][1])
            self._side2.side_cmbx.set_active(0)

    def _update_attributes(self):
        self._rotate_facing = 0
        self._rotate_reverse = 0
        if self._side1.cbutton.get_active():
            if self._side1.side_cmbx.get_active_index() == "both":
                self._rotate_facing = self._side1.angle_cmbx.get_active_index()
                self._rotate_reverse = self._rotate_reverse
            elif self._side1.side_cmbx.get_active_index() == "facing":
                self._rotate_facing = self._side1.angle_cmbx.get_active_index()
            else:
                self._rotate_reverse = self._side1.angle_cmbx.get_active_index()

            if self._side2.cbutton.get_active():
                if self._side2.side_cmbx.get_active_index() == "facing":
                    self._rotate_facing = self._side2.angle_cmbx.get_active_index()
                else:
                    self._rotate_reverse = self._side2.angle_cmbx.get_active_index()

    def _update_gui(self):
        if self._rotate_facing or self._rotate_reverse:
            self._side1.cbutton.set_active(True)

        if self._rotate_facing == self._rotate_reverse:
            self._side1.side_cmbx.set_active_index("both")
            self._side1.angle_cmbx.set_active_index(self._rotate_facing)

        elif self._rotate_facing:
            self._side1.side_cmbx.set_active_index("facing")
            self._side1.angle_cmbx.set_active_index(self._rotate_facing)
            if self._rotate_reverse:
                self._side2.cbutton.set_active(True)
                self._side2.side_cmbx.set_active_index("reverse")
                self._side2.angle_cmbx.set_active_index(self._rotate_reverse)

        else:
            self._side1.side_cmbx.set_active_index("reverse")
            self._side1.angle_cmbx.set_active_index(self._rotate_reverse)
