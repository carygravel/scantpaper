"Data and methods for profiles of scan options"

from copy import deepcopy
import uuid
from gi.repository import GObject
import sane


class Profile(GObject.Object):
    """Have to subclass Glib::Object to be able to name it as an object in
    Glib::ParamSpec->object in Gscan2pdf::Dialog::Scan"""

    frontend = None
    backend = None

    def __init__(self, frontend=None, backend=None, uid=None):
        super().__init__()
        if frontend is None:
            self.frontend = {}
        else:
            self.frontend = deepcopy(frontend)
        if backend is None:
            self.backend = []
        else:
            self.backend = deepcopy(backend)
            self.map_from_cli()

        # add uuid to identify later which callback has finished
        self.uuid = str(uuid.uuid1()) if uid is None else uid

    def __copy__(self):
        return Profile(frontend=self.frontend, backend=self.backend, uid=self.uuid)

    def __str__(self):
        return f"Profile(frontend={self.frontend}, backend={self.backend}, uuid={self.uuid})"

    def __eq__(self, other):
        return self.frontend == other.frontend and self.backend == other.backend

    def add_backend_option(self, name, val, oldval=None):
        """the oldval option is a hack to allow us not to apply geometry options
        if setting paper as part of a profile"""
        if name is None or name == "":
            raise ValueError("Error: no option name")

        if oldval is not None and val == oldval:
            return
        self.backend.append((name, val))

        # Note any duplicate options, keeping only the last entry.
        seen = {}
        for i in self.each_backend_option(True):
            (nam, _value) = self.get_backend_option_by_index(i)
            synonyms = _synonyms(nam)
            for key in synonyms:
                if key in seen:
                    self.remove_backend_option_by_index(i)
                    break
                seen[key] = True

        self.uuid = str(uuid.uuid1())

    def get_backend_option_by_index(self, i):
        "get_backend_option_by_index"
        return self.backend[i]

    def remove_backend_option_by_index(self, i):
        "remove_backend_option_by_index"
        del self.backend[i]
        self.uuid = str(uuid.uuid1())

    def remove_backend_option_by_name(self, name):
        "remove_backend_option_by_name"
        i = None
        for i in self.each_backend_option():
            key, _val = self.get_backend_option_by_index(i)
            if key == name:
                break

        if i <= self.num_backend_options():
            del self.backend[i]

        self.uuid = str(uuid.uuid1())

    def each_backend_option(self, backwards=False):
        "an iterator for backend options"
        i = len(self.backend) - 1 if backwards else 0
        while -1 < i < len(self.backend):
            yield i
            i = i - 1 if backwards else i + 1

    def num_backend_options(self):
        "num_backend_options"
        return len(self.backend)

    def add_frontend_option(self, name, val):
        "add_frontend_option"
        if name is None or name == "":
            raise ValueError("Error: no option name")

        self.frontend[name] = val
        self.uuid = str(uuid.uuid1())

    def each_frontend_option(self):
        "an iterator for frontend options"
        yield from self.frontend.keys()

    def get_frontend_option(self, name):
        "get_frontend_option"
        return self.frontend[name]

    def remove_frontend_option(self, name):
        "remove_frontend_option"
        if name in self.frontend:
            del self.frontend[name]

    def get(self):
        "return a dict of frontend and backend options"
        return {"frontend": self.frontend, "backend": self.backend}

    def map_from_cli(self):
        """Map scanimage and scanadf (CLI) geometry options to the backend geometry names"""
        new = Profile()
        for i in self.each_backend_option():
            name, val = self.get_backend_option_by_index(i)
            if name == "l":
                new.add_backend_option("tl-x", val)

            elif name == "t":
                new.add_backend_option("tl-y", val)

            elif name == "x":
                _l = self.get_option_by_name("l")
                if _l is None:
                    _l = self.get_option_by_name("tl-x")
                if _l is not None:
                    val += _l
                new.add_backend_option("br-x", val)

            elif name == "y":
                _t = self.get_option_by_name("t")
                if _t is None:
                    _t = self.get_option_by_name("tl-y")
                if _t is not None:
                    val += _t
                new.add_backend_option("br-y", val)

            else:
                new.add_backend_option(name, val)
        self.backend = deepcopy(new.backend)

    def map_to_cli(self, options):
        """Map backend geometry options to the scanimage and scanadf (CLI) geometry names"""
        new = Profile()
        for i in self.each_backend_option():
            (name, val) = self.get_backend_option_by_index(i)
            if name == "tl-x":
                new.add_backend_option("l", val)

            elif name == "tl-y":
                new.add_backend_option("t", val)

            elif name == "br-x":
                _l = self.get_option_by_name("l")
                if _l is None:
                    _l = self.get_option_by_name("tl-x")
                if _l is not None:
                    val -= _l
                new.add_backend_option("x", val)

            elif name == "br-y":
                _t = self.get_option_by_name("t")
                if _t is None:
                    _t = self.get_option_by_name("tl-y")
                if _t is not None:
                    val -= _t
                new.add_backend_option("y", val)

            else:
                if options is not None:
                    opt = options.by_name(name)
                    if "type" in opt and opt["type"] == sane._sane.TYPE_BOOL:
                        val = "yes" if val else "no"

                new.add_backend_option(name, val)

        new.frontend = deepcopy(self.frontend)

        return new

    def get_option_by_name(self, name):
        """Extract a option value from a profile"""
        for i in self.each_backend_option():
            (key, val) = self.get_backend_option_by_index(i)
            if key == name:
                return val

        return None


def _synonyms(name):

    synonyms = [
        ["page-height", "pageheight"],
        ["page-width", "pagewidth"],
        ["tl-x", "l"],
        ["tl-y", "t"],
        ["br-x", "x"],
        ["br-y", "y"],
    ]
    for synonym in synonyms:
        if name in synonym:
            return synonym

    return [name]
