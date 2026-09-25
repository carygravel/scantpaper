"""Typed helpers for GObject integration (gi.repository has no type stubs)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

_T = TypeVar("_T")


class _Property(Generic[_T]):
    """Typed stand-in for a GObject.Property descriptor."""

    def __get__(self, instance: object, owner: type) -> _T:
        """Return the property value when accessed on an instance."""
        raise NotImplementedError  # pragma: no cover

    def __set__(self, instance: object, value: object) -> None:
        """Accept a property value when assigned on an instance."""
        raise NotImplementedError  # pragma: no cover

    def __delete__(self, instance: object) -> None:
        """Delete the property value on an instance."""
        raise NotImplementedError  # pragma: no cover

    def setter(self, _f: Callable[..., None]) -> _Property[_T]:
        """Return the descriptor for use as a setter decorator."""
        return self  # pragma: no cover


def property_(
    *args: object, **kwargs: object
) -> Callable[[Callable[..., _T]], _Property[_T]]:
    """Wrap ``GObject.Property`` so the decorator has a known return type."""
    return cast(
        "Callable[[Callable[..., _T]], _Property[_T]]",
        GObject.Property(*args, **kwargs),
    )
