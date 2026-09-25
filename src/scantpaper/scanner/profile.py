"""Data and methods for profiles of scan options."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from gi.repository import GObject

from scantpaper.frontend import enums

if TYPE_CHECKING:
    from collections.abc import Iterator

    from scantpaper.scanner.options import Options


class Profile(GObject.Object):
    """Subclass Glib.Object for use in Glib.ParamSpec in Scantpaper.Dialog.Scan."""

    frontend: dict[str, object]
    backend: list[tuple[str, object] | dict[str, object]]

    def __init__(
        self,
        frontend: dict[str, object] | None = None,
        backend: list[tuple[str, object] | dict[str, object]] | None = None,
        uid: str | None = None,
    ) -> None:
        """Initialise the profile with deep-copied frontend and backend dicts."""
        super().__init__()
        if isinstance(frontend, dict) and "frontend" in frontend:
            backend = cast(
                "list[tuple[str, object] | dict[str, object]]",
                frontend.get("backend", []),
            )
            frontend = cast("dict[str, object]", frontend["frontend"])

        if frontend is None:
            self.frontend = {}
        else:
            self.frontend = deepcopy(frontend)

            # if we have just pulled a profile from pre-v3 gscan2pdf config,
            # ensure num_pages is an int
            if "num_pages" in self.frontend:
                self.frontend["num_pages"] = int(self.frontend["num_pages"])
        if backend is None:
            self.backend = []
        else:
            self.backend = deepcopy(backend)

            # if we have just pulled a profile from pre-v3 gscan2pdf config,
            # then convert the dict pairs to tuples
            for i, opt in enumerate(self.backend):
                if isinstance(opt, dict):
                    name = next(iter(opt.keys()))
                    val = opt[name]
                    self.backend[i] = (name, val)

            self.map_from_cli()

        # add uuid to identify later which callback has finished
        self.uuid = str(uuid.uuid1()) if uid is None else uid

    def __copy__(self) -> Profile:
        """Return a shallow copy with deep-copied frontend and backend."""
        return Profile(frontend=self.frontend, backend=self.backend, uid=self.uuid)

    def __str__(self) -> str:
        """Return a string representation of the profile."""
        return f"Profile(frontend={self.frontend}, backend={self.backend}, uuid={self.uuid})"

    def __eq__(self, other: object) -> bool:
        """Compare profiles by frontend and backend dicts only."""
        return self.frontend == other.frontend and self.backend == other.backend

    __hash__ = None

    def add_backend_option(
        self, name: str | None, val: object, oldval: object | None = None
    ) -> None:
        """Skip geometry options when setting paper as part of a profile."""
        if name is None or name == "":
            msg = "Error: no option name"
            raise ValueError(msg)

        if oldval is not None and val == oldval:
            return
        self.backend.append((name, val))

        # Note any duplicate options, keeping only the last entry.
        seen = {}
        for i in self.each_backend_option(backwards=True):
            nam, _value = self.get_backend_option_by_index(i)
            synonyms = _synonyms(nam)
            for key in synonyms:
                if key in seen:
                    self.remove_backend_option_by_index(i)
                    break
                seen[key] = True

        self.uuid = str(uuid.uuid1())

    def get_backend_option_by_index(
        self, i: int
    ) -> tuple[str, object] | dict[str, object]:
        """get_backend_option_by_index."""
        return self.backend[i]

    def remove_backend_option_by_index(self, i: int) -> None:
        """remove_backend_option_by_index."""
        del self.backend[i]
        self.uuid = str(uuid.uuid1())

    def remove_backend_option_by_name(self, name: str) -> None:
        """remove_backend_option_by_name."""
        i = None
        for i in self.each_backend_option():
            key, _val = self.get_backend_option_by_index(i)
            if key == name:
                break

        if cast("int", i) <= self.num_backend_options():
            del self.backend[i]

        self.uuid = str(uuid.uuid1())

    def each_backend_option(self, *, backwards: bool = False) -> Iterator[int]:
        """Iterate over backend options."""
        i = len(self.backend) - 1 if backwards else 0
        while -1 < i < len(self.backend):
            yield i
            i = i - 1 if backwards else i + 1

    def num_backend_options(self) -> int:
        """num_backend_options."""
        return len(self.backend)

    def add_frontend_option(self, name: str | None, val: object) -> None:
        """add_frontend_option."""
        if name is None or name == "":
            msg = "Error: no option name"
            raise ValueError(msg)

        self.frontend[name] = val
        self.uuid = str(uuid.uuid1())

    def each_frontend_option(self) -> Iterator[str]:
        """Iterate over frontend options."""
        yield from self.frontend.keys()

    def get_frontend_option(self, name: str) -> object:
        """get_frontend_option."""
        return self.frontend[name]

    def remove_frontend_option(self, name: str) -> None:
        """remove_frontend_option."""
        if name in self.frontend:
            del self.frontend[name]

    def get(
        self,
    ) -> dict[str, dict[str, object] | list[tuple[str, object] | dict[str, object]]]:
        """Return a dict of frontend and backend options."""
        return {"frontend": self.frontend, "backend": self.backend}

    def map_from_cli(self) -> None:
        """Map scanimage and scanadf (CLI) geometry options to the backend geometry names."""
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
                    val = cast("float", val) + cast("float", _l)
                new.add_backend_option("br-x", val)

            elif name == "y":
                _t = self.get_option_by_name("t")
                if _t is None:
                    _t = self.get_option_by_name("tl-y")
                if _t is not None:
                    val = cast("float", val) + cast("float", _t)
                new.add_backend_option("br-y", val)

            else:
                new.add_backend_option(name, val)
        self.backend = deepcopy(new.backend)

    def _subtract_offset(self, val: float, name_from: str, name_to: str) -> float:
        """Subtract the geometry origin from a width or height value."""
        offset = self.get_option_by_name(name_from)
        if offset is None:
            offset = self.get_option_by_name(name_to)
        if offset is not None:
            val -= cast("float", offset)
        return val

    def _add_cli_option(
        self, options: Options | None, new: Profile, name: str, val: object
    ) -> None:
        if options is not None:
            opt = options.by_name(name)
            if (
                "type" in cast("dict[str, object]", opt)
                and cast("Any", opt)["type"] == enums.TYPE_BOOL
            ):
                val = "yes" if val else "no"

        new.add_backend_option(name, val)

    def map_to_cli(self, options: Options | None) -> Profile:
        """Map backend geometry options to the scanimage and scanadf (CLI) geometry names."""
        new = Profile()
        for i in self.each_backend_option():
            name, val = self.get_backend_option_by_index(i)
            if name == "tl-x":
                new.add_backend_option("l", val)

            elif name == "tl-y":
                new.add_backend_option("t", val)

            elif name == "br-x":
                new.add_backend_option("x", self._subtract_offset(val, "l", "tl-x"))

            elif name == "br-y":
                new.add_backend_option("y", self._subtract_offset(val, "t", "tl-y"))

            else:
                self._add_cli_option(options, new, name, val)

        new.frontend = deepcopy(self.frontend)

        return new

    def get_option_by_name(self, name: str) -> object | None:
        """Extract a option value from a profile."""
        for i in self.each_backend_option():
            key, val = self.get_backend_option_by_index(i)
            if key == name:
                return val

        return None


def _synonyms(name: str) -> list[str]:

    synonyms: list[list[str]] = [
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
