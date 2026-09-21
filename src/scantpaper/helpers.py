"""Various helper functions."""

from __future__ import annotations

import datetime
import locale
import logging
import pathlib
import re
import subprocess
import weakref
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from scantpaper.const import FRACTIONAL_DIGITS
from scantpaper.dialog import MultipleMessage
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from os import PathLike
    from typing import TextIO

    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

logger = logging.getLogger(__name__)

PROCESS_FAILED = -1
SETTING = {}
_MESSAGE_DIALOG = {"dialog": None}


@lru_cache
def decimal_separator() -> str:
    """Return the decimal separator of the configured locale.

    The separator is read from the environment rather than the ambient
    LC_NUMERIC, because other code temporarily flips LC_NUMERIC to "C".
    The previous LC_NUMERIC state is restored before returning.
    """
    previous = locale.setlocale(locale.LC_NUMERIC, None)
    locale.setlocale(locale.LC_NUMERIC, "")
    sep = locale.localeconv()["decimal_point"]
    locale.setlocale(locale.LC_NUMERIC, previous)
    return sep


@lru_cache
def grouping_separator() -> str:
    """Return the digit grouping separator of the configured locale.

    Mirrors decimal_separator(): read from the environment, restore the
    previous LC_NUMERIC state. May be empty for locales without digit
    grouping, such as "C".
    """
    previous = locale.setlocale(locale.LC_NUMERIC, None)
    locale.setlocale(locale.LC_NUMERIC, "")
    sep = locale.localeconv()["thousands_sep"]
    locale.setlocale(locale.LC_NUMERIC, previous)
    return sep


def format_number(number: float) -> str:
    """Format a number with the locale's decimal separator.

    Whole numbers keep no decimal part (210 not 210.0), while fractional
    values use the locale's separator (115,2 in a comma locale). Fractional
    precision follows Python's :g formatting.
    """
    text = f"{number:g}"
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(".", sep)
    return text


def format_number_precise(number: float) -> str:
    """Format a number with the locale separator, keeping full precision.

    Scan-option values must round-trip unchanged (e.g. 1.07818603515625), so
    the text keeps str()'s precision and only the separator is localized.
    """
    text = str(number)
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(".", sep)
    return text


def parse_number(
    text: str, number_type: type[int | float] = float, *, strict: bool = True
) -> int | float:
    """Parse user-entered text into a number, accepting the locale's separator.

    With strict=True only digits, a single locale decimal separator and
    right-aligned groups of three digits separated by the locale grouping
    separator are accepted; anything else raises ValueError. With
    strict=False the historical lenient behaviour is kept: the first locale
    decimal separator is translated and the rest is handed to number_type.
    """
    if strict:
        _validate_strict_number(text)
        grp = grouping_separator()
        if grp:
            text = text.replace(grp, "")
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(sep, ".", 1)
    return number_type(text)


def _validate_strict_number(text: str) -> None:
    """Raise ValueError when text is not a number written in the locale."""
    dec = re.escape(decimal_separator())
    if grp := grouping_separator():
        grp = re.escape(grp)
        pattern = rf"^[+-]?(\d{{1,3}}({grp}\d{{3}})*|\d+)({dec}\d*)?$"
    else:
        pattern = rf"^[+-]?\d+({dec}\d*)?$"
    if not re.fullmatch(pattern, text):
        msg = f"'{text}' is not a number in this locale"
        raise ValueError(msg)


def spin_step(constraint: tuple[float, float, float]) -> int:
    """Whole-unit step for a ranged option, ignoring any fractional step."""
    if constraint[2] > 0:
        return max(1, int(constraint[2]))
    return 1


def fractional_digits(value: float, max_digits: int = FRACTIONAL_DIGITS) -> int:
    """Display precision for a numeric value, at most ``max_digits``.

    Trailing zeros are trimmed, so a whole value renders with 0 fractional
    digits, a value with one non-zero fraction digit with 1, and so on up to
    ``max_digits`` (``FRACTIONAL_DIGITS`` by default).
    """
    fraction = f"{value:.{max_digits}f}".partition(".")[2]
    return len(fraction.rstrip("0"))


def configure_fractional_spinbutton(
    widget: Gtk.SpinButton, digits: int = FRACTIONAL_DIGITS
) -> None:
    """Make a spin button fractional, locale-correct and strictly validated.

    Clears GTK's ``numeric`` filter so the locale decimal separator survives
    typing, keeps the displayed digits value-driven (trailing zeros are
    trimmed), and reverts any commit whose text is not a number written with
    the locale's separators.
    """
    widget.set_numeric(False)
    widget.set_digits(digits)

    def value_changed_trim_cb(_widget: Gtk.SpinButton) -> None:
        _widget.set_digits(fractional_digits(_widget.get_value(), digits))

    def commit_validate_cb(_widget: Gtk.SpinButton, *_args: object) -> None:
        try:
            parse_number(_widget.get_text())
        except ValueError:
            _widget.set_value(_widget.get_value())

    widget.connect("value-changed", value_changed_trim_cb)
    widget.connect("focus-out-event", commit_validate_cb)
    widget.connect("activate", commit_validate_cb)
    widget.set_digits(fractional_digits(widget.get_value(), digits))


def _weak_callback(obj: object, method_name: str) -> Callable[..., object | None]:
    """Create a weak callback."""
    ref = weakref.ref(obj)

    def callback(*args: object, **kwargs: object) -> object | None:
        instance = ref()
        if instance:
            return getattr(instance, method_name)(*args, **kwargs)
        return None

    return callback


@dataclass
class Proc:
    """Class for passing returncode, stdout & stderr."""

    returncode: int
    stdout: str | None
    stderr: str


def exec_command(cmd: list[str], pidfile: TextIO | None = None) -> Proc:
    """Wrap subprocess.Popen()."""
    logger.info(" ".join(cmd))
    try:
        # Put the child in its own session so that cancel() can killpg() it
        # without taking down the process group of the whole application.
        with subprocess.Popen(  # noqa: S603 - cmd from internal call sites; explicit shell=False
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=locale.getpreferredencoding(),
            start_new_session=pidfile is not None,
        ) as proc:
            logger.info("Spawned PID %s", proc.pid)
            if pidfile is not None:
                pidfile.write(str(proc.pid))
                pidfile.flush()
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
    except FileNotFoundError as err:
        returncode, stdout_data, stderr_data = -1, None, str(err)

    return Proc(returncode, stdout_data, stderr_data)


def exec_command_run(  # noqa: PLR0913 - mirrors subprocess.run()'s surface; keyword-only after cmd/pidfile
    cmd: str | list[str],
    pidfile: TextIO | None = None,
    *,
    check: bool = False,
    capture_output: bool = False,
    text: bool = True,
    shell: bool = False,
    **kwargs: object,
) -> subprocess.CompletedProcess:
    """Run a command like subprocess.run() but record the spawn pid for cancellation."""
    kwargs = dict(kwargs)
    if pidfile is not None:
        kwargs["start_new_session"] = True
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    kwargs["text"] = text
    try:
        with subprocess.Popen(  # noqa: S603 - shell forwarded deliberately; defaults to False
            cmd,
            shell=shell,
            encoding=locale.getpreferredencoding(),
            **cast("Any", kwargs),
        ) as proc:
            if pidfile is not None:
                pidfile.write(str(proc.pid))
                pidfile.flush()
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
    except FileNotFoundError as err:
        if check:
            raise
        return subprocess.CompletedProcess(cmd, PROCESS_FAILED, None, str(err))
    if check and returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, cmd, output=stdout_data, stderr=stderr_data
        )
    return subprocess.CompletedProcess(cmd, returncode, stdout_data, stderr_data)


def program_version(
    stream: str, regex: str | re.Pattern[str], cmd: list[str]
) -> str | None:
    """Run command and parse version string from output."""
    return _program_version(stream, regex, exec_command(cmd))


def _program_version(
    stream: str, regex: str | re.Pattern[str], proc: Proc
) -> str | None:
    if proc.stdout is None:
        proc.stdout = ""
    if proc.stderr is None:
        proc.stderr = ""
    output = None
    if stream == "stdout":
        output = proc.stdout

    elif stream == "stderr":
        output = proc.stderr

    elif stream == "both":
        output = proc.stdout + proc.stderr

    else:
        logger.error("Unknown stream: '%s'", (stream,))

    regex2 = re.search(regex, output) if output is not None else None
    if regex2:
        return regex2.group(1)
    if proc.returncode == PROCESS_FAILED:
        logger.info(proc.stderr)
        return None

    logger.info("Unable to parse version string from: '%s'", output)
    return None


def collate_metadata(
    settings: dict[str, object], today_and_now: datetime.datetime
) -> dict[str, object]:
    """Collect metadata from settings dictionary."""
    metadata = {}
    for key in ["author", "title", "subject", "keywords"]:
        if key in settings:
            metadata[key] = settings[key]
    metadata["datetime"] = today_and_now + settings["datetime offset"]
    if "use_time" not in settings:
        metadata["datetime"] = metadata["datetime"].replace(hour=0, minute=0, second=0)

    if "use_timezone" not in settings:
        metadata["datetime"] = metadata["datetime"].replace(
            tzinfo=datetime.timezone.utc
        )
    return metadata


def expand_metadata_pattern(**kwargs: object) -> str:
    """Expand metadata template."""
    # Expand author, title and extension
    for key in ["author", "title", "subject", "keywords", "extension"]:
        if key not in kwargs or kwargs[key] is None:
            kwargs[key] = ""
        regex = r"%D" + key[0]
        kwargs["template"] = re.sub(
            regex,
            str(kwargs[key]),
            str(kwargs["template"]),
            flags=re.MULTILINE | re.DOTALL,
        )

    # Expand convert %Dx code to %x, convert using strftime and replace
    regex = re.search(
        r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
    )
    while regex:
        code = regex.group(1)
        template = f"%{code}"
        result = kwargs["docdate"].strftime(template)
        kwargs["template"] = re.sub(
            rf"%D{code}",
            result,
            kwargs["template"],
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        regex = re.search(
            r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
        )

    # Expand basic strftime codes
    kwargs["template"] = kwargs["today_and_now"].strftime(kwargs["template"])

    # avoid leading and trailing whitespace in expanded filename template
    kwargs["template"] = kwargs["template"].strip()
    if kwargs.get("convert_whitespace"):
        kwargs["template"] = re.sub(
            r"\s", r"_", kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )
    return kwargs["template"]


def show_message_dialog(**options: object) -> None:
    """Show message dialog."""
    dialog = _MESSAGE_DIALOG["dialog"]
    if not dialog:
        dialog = MultipleMessage(title=_("Messages"), transient_for=options["parent"])
        dialog.set_default_size(
            SETTING["message_window_width"], SETTING["message_window_height"]
        )
        _MESSAGE_DIALOG["dialog"] = dialog

    options["responses"] = SETTING["message"]
    dialog.add_message(options)

    response = None
    if dialog.grid_rows > 1:
        dialog.show_all()
        response = dialog.run()

    if response is not None:
        dialog.store_responses(response, SETTING["message"])
    (
        SETTING["message_window_width"],
        SETTING["message_window_height"],
    ) = dialog.get_size()
    dialog.destroy()


def get_tmp_dir(dirname: str | None, pattern: str) -> str | None:
    """If user selects session dir as tmp dir, return parent dir."""
    if dirname is None:
        return None
    while re.search(pattern, dirname):
        dirname = str(pathlib.Path(dirname).parent)
    return dirname


def slurp(file: str | PathLike[str] | TextIO) -> str:
    """Slurp file."""
    if hasattr(file, "read"):
        file.seek(0)
        content = file.read()
        if isinstance(content, bytes):
            return content.decode("utf-8", "replace")
        return content
    with pathlib.Path(file).open(encoding="utf-8") as fhd:
        return fhd.read()


def recursive_slurp(files: Iterable[str | PathLike[str]]) -> None:
    """Recursively process files and directories, logging the contents of each file."""
    for file in files:
        if pathlib.Path(file).is_dir():
            recursive_slurp(pathlib.Path(file).glob("*"))
        else:
            output = slurp(file)
            if output is not None:
                output = output.rstrip()
                logger.info(output)
