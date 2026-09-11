"""helper functions to read and write config."""

import datetime
import json
import logging
import os
import pathlib
import re
import shutil
from types import SimpleNamespace

import gi

from scantpaper.const import SELECTORDRAGGER_TOOL
from scantpaper.helpers import slurp
from scantpaper.i18n import _

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk  # noqa: E402

DEFAULTS = {
    "window_width": 800,
    "window_height": 600,
    "window_maximize": True,
    "window_x": 0,
    "window_y": 0,
    "thumb panel": 100,
    "viewer_tools": "tabbed",
    "image_control_tool": SELECTORDRAGGER_TOOL,
    "scan_window_width": None,
    "scan_window_height": None,
    "message_window_width": 600,
    "message_window_height": 200,
    "TMPDIR": None,
    "Page range": "all",
    "version": None,
    "SANE version": None,
    "selection": None,
    "cwd": None,
    "title": None,
    "title-suggestions": None,
    "author": None,
    "author-suggestions": None,
    "subject": None,
    "subject-suggestions": None,
    "keywords": None,
    "keywords-suggestions": None,
    "downsample": False,
    "downsample dpi": 150,
    "cache options": True,
    "cache": None,
    "restore window": True,
    "set_timestamp": True,
    "use_time": False,
    "use_timezone": True,
    "datetime offset": datetime.timedelta(seconds=0),
    "pdf compression": "auto",
    "tiff compression": None,
    "quality": 75,
    "image type": "pdf",
    "device": None,
    "cache-device-list": True,
    "device list": [],
    "device blacklist": None,
    "unpaper on scan": False,
    "unpaper options": None,
    "unsharp radius": 0,
    "unsharp percentage": 50,
    "unsharp threshold": 0.05,
    "allow-batch-flatbed": False,
    "cancel-between-pages": False,
    "adf-defaults-scan-all-pages": True,
    "cycle sane handle": False,
    "ignore-duplex-capabilities": False,
    "profile": {},
    "default profile": None,
    "default-scan-options": None,
    "rotate facing": 0,
    "rotate reverse": 0,
    "default filename": "%Da %DY-%Dm-%Dd.%De",
    "convert whitespace to underscores": False,
    "view files toggle": True,
    "threshold-before-ocr": False,
    "brightness tool": 65,
    "contrast tool": 65,
    "threshold tool": 20,
    "Blank threshold": 0.005,  # Blank page standard deviation threshold
    "Dark threshold": 0.12,  # Dark page mean threshold
    "OCR on scan": True,
    "ocr engine": "tesseract",
    "ocr language": None,
    "OCR output": "replace",  # When a page is re-OCRed, replace old text with new text
    "ps_backend": "pdftops",
    "user_defined_tools": ["gimp %i"],
    "udt_on_scan": False,
    "current_udt": None,
    "post_save_hook": False,
    "current_psh": None,
    "auto-open-scan-dialog": True,
    "available-tmp-warning": 10,
    "close_dialog_on_save": True,
    "Paper": {
        _("A3"): {
            "x": 297,
            "y": 420,
            "l": 0,
            "t": 0,
        },
        _("A4"): {
            "x": 210,
            "y": 297,
            "l": 0,
            "t": 0,
        },
        _("US Letter"): {
            "x": 216,
            "y": 279,
            "l": 0,
            "t": 0,
        },
        _("US Legal"): {
            "x": 216,
            "y": 356,
            "l": 0,
            "t": 0,
        },
    },
    "message": {},
}


def _get_convert_command():
    """Determine the correct imagemagick command."""
    if shutil.which("magick"):
        return "magick"
    return "convert"


CONVERT_COMMAND = _get_convert_command()
logger = logging.getLogger(__name__)

_LOCAL_TZ = datetime.datetime.now().astimezone().tzinfo

# Release version that introduced the colour-aware threshold. Configs written
# by older versions have their "threshold tool" value migrated to the new
# ink-strength scale (v -> 100 - v). Keep in sync with the release version.
THRESHOLD_MIGRATION_VERSION = (3, 0, 16)


def _version_tuple(version):
    """Parse a version string into a comparable tuple of integers."""
    if not version:
        return (0,)
    return tuple(int(x) for x in re.findall(r"\d+", str(version))[:3])


class ConfigDict(dict):
    """A dict that carries warnings raised while loading the configuration."""

    def __init__(self, *args, **kwargs):
        """Initialise ConfigDict."""
        super().__init__(*args, **kwargs)
        self.load_warnings = []


_SALVAGE_PATTERN = re.compile(r'"([^"]+)"\s*:\s*')


def _salvage_config(configstr):
    """Salvage ``"key": <value>`` fragments from an unparseable config file."""
    rescued = ConfigDict()
    decoder = json.JSONDecoder()
    for match in _SALVAGE_PATTERN.finditer(configstr):
        key = match.group(1)
        if key not in DEFAULTS or key in rescued:
            continue
        try:
            value, _end = decoder.raw_decode(configstr, match.end())
        except json.JSONDecodeError:
            continue
        rescued[key] = value
    return rescued


def _coerce_bool(value):
    """Return a lossless bool coercion of value, or None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in ("true", "false", "0", "1"):
        return value.lower() in ("true", "1")
    return None


def _coerce_int(value):
    """Return a lossless int coercion of value, or None."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value):
    """Return a lossless float coercion of value, or None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value):
    """Return a lossless str coercion of value, or None."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


_COERCE_TO_TYPE = {
    bool: _coerce_bool,
    int: _coerce_int,
    float: _coerce_float,
    str: _coerce_str,
}


def _coerce_to_type(value, target_type):
    """Return a lossless coercion of value to target_type, or None."""
    coerce = _COERCE_TO_TYPE.get(target_type)
    if coerce is None:
        return None
    return coerce(value)


def _normalise_types(config):
    """Coerce wrongly typed known settings to their default's type.

    Keys whose default is None are skipped, as are values that already match
    the default's type. A value that cannot be coerced is kept as it is,
    with a warning.
    """
    for key, default in DEFAULTS.items():
        if key not in config or default is None:
            continue
        if type(config[key]) is type(default):
            continue
        value = config[key]
        coerced = _coerce_to_type(value, type(default))
        if coerced is None:
            config.load_warnings.append(
                _(
                    "The setting %s is %r and cannot be used as %s, so it has "
                    "been left unchanged."
                )
                % (key, value, type(default).__name__)
            )
        else:
            config[key] = coerced
            config.load_warnings.append(
                _("The setting %s is %r and has been converted to %r.")
                % (key, value, coerced)
            )


def read_config(filename):
    """Read the config."""
    config = ConfigDict()
    logger.info("Reading config from %s", filename)
    if not os.access(filename, os.R_OK):
        with pathlib.Path(filename).open("w", encoding="utf-8") as fh:
            fh.write("")

    configstr = slurp(filename)
    if len(configstr) > 0:
        try:
            config = ConfigDict(json.loads(configstr))
        except json.decoder.JSONDecodeError:
            logger.exception(
                "Error: unable to load settings.\nBacking up settings\nReverting to defaults"
            )
            backup = pathlib.Path(f"{filename}.old")
            pathlib.Path(filename).rename(backup)
            config = _salvage_config(configstr)
            if config:
                config.load_warnings.append(
                    _(
                        "The settings file %s could not be read in full. The "
                        "following settings were restored: %s. The rest were "
                        "reset to their defaults. A backup of the original "
                        "file has been saved as %s."
                    )
                    % (filename, ", ".join(sorted(config)), backup)
                )
            else:
                config.load_warnings.append(
                    _(
                        "The settings file %s could not be read, so all "
                        "settings have been reset to their defaults. A backup "
                        "of the original file has been saved as %s."
                    )
                    % (filename, backup)
                )

    _deserialise_and_migrate(config)
    _normalise_types(config)

    logger.debug(config)
    return config


def _deserialise_and_migrate(config):
    """Deserialise stored values and apply legacy migrations in place."""
    if "user_defined_tools" in config and not isinstance(
        config["user_defined_tools"], list
    ):
        config["user_defined_tools"] = [config["user_defined_tools"]]

    # deserialise device list
    if (
        isinstance(config.get("device list"), list)
        and len(config["device list"]) > 0
        and isinstance(config["device list"][0], dict)
    ):
        config["device list"] = [SimpleNamespace(**x) for x in config["device list"]]

    _normalise_profiles(config)

    # deserialise timedelta
    if (
        isinstance(config.get("datetime offset"), list)
        and len(config["datetime offset"]) == 4
    ):
        config["datetime offset"] = datetime.timedelta(
            days=config["datetime offset"][0],
            hours=config["datetime offset"][1],
            minutes=config["datetime offset"][2],
            seconds=config["datetime offset"][3],
        )

    # deserialise selection
    if isinstance(config.get("selection"), dict):
        selection = Gdk.Rectangle()
        selection.x, selection.y, selection.width, selection.height = (
            config["selection"]["x"],
            config["selection"]["y"],
            config["selection"]["width"],
            config["selection"]["height"],
        )
        config["selection"] = selection

    _remove_legacy_int_tools(config)
    _migrate_threshold_tool(config)


def _normalise_profiles(config):
    """Remove undefined profiles and normalise legacy pre-v3 ones.

    Profiles written by gscan2pdf 2.x may be backend-only with no frontend
    key; give them both keys so downstream consumers never key-error.
    """
    profiles = config.get("profile")
    if not isinstance(profiles, dict):
        return

    # remove undefined profiles
    for name in list(profiles.keys()):
        if not profiles[name]:
            del profiles[name]

    # normalise legacy pre-v3 profiles that lack a frontend key
    for profile in profiles.values():
        if isinstance(profile, dict):
            profile.setdefault("frontend", {})
            profile.setdefault("backend", [])


def _remove_legacy_int_tools(config):
    """Remove old int tool values - these are now strings."""
    for k in "image_control_tool", "viewer_tools":
        if k in config and isinstance(config[k], int):
            del config[k]


def _migrate_threshold_tool(config):
    """Migrate the threshold tool value from the pre-colour-aware scale.

    The old slider was a raw 0-255 cutoff despite its 0-100 range; 100 - v
    preserves the cut-off the user intended on the new ink-strength scale.
    """
    if (
        "threshold tool" in config
        and isinstance(config["threshold tool"], int)
        and _version_tuple(config.get("version")) < THRESHOLD_MIGRATION_VERSION
    ):
        config["threshold tool"] = 100 - config["threshold tool"]


def add_defaults(config):
    """Add defaults."""
    # remove unused settings
    for k in list(config.keys()):
        if k not in DEFAULTS:
            del config[k]

    # add default settings
    for k, v in DEFAULTS.items():
        if k not in config:
            config[k] = v


def remove_invalid_paper(hashref):
    """Remove invalid paper formats."""
    for paper in list(hashref.keys()):
        if paper in ["<>", "</>"]:
            del hashref[paper]
        else:
            for opt in ["x", "y", "t", "l"]:
                if not isinstance(hashref[paper], dict) or opt not in hashref[paper]:
                    del hashref[paper]
                    break


def write_config(rc, config):
    """Write config."""
    output = dict(config)
    # serialise device list
    if "device list" in output and isinstance(output["device list"], list):
        dl = []
        for dns in output["device list"]:
            d = {}
            for key in ["name", "vendor", "model", "label"]:
                if hasattr(dns, key):
                    d[key] = getattr(dns, key)
            dl.append(d)
        output["device list"] = dl

    # serialise timedelta
    if isinstance(output.get("datetime offset"), datetime.timedelta):
        output["datetime offset"] = [
            output["datetime offset"].days,
            output["datetime offset"].seconds // 3600,
            (output["datetime offset"].seconds // 60) % 60,
            output["datetime offset"].seconds % 60,
        ]

    # serialise selection
    if isinstance(output.get("selection"), Gdk.Rectangle):
        selection = {}
        selection["x"], selection["y"], selection["width"], selection["height"] = (
            output["selection"].x,
            output["selection"].y,
            output["selection"].width,
            output["selection"].height,
        )
        output["selection"] = selection

    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(output, sort_keys=True, indent=4))
    logger.info("Wrote config to %s", rc)


def update_config_from_imported_metadata(config, metadata):
    """Update config from imported metadata."""
    for name in ["author", "title", "subject", "keywords"]:
        if name in metadata:
            config[name] = metadata[name]
    if "datetime" in metadata and metadata["datetime"] is not None:
        config["datetime offset"] = metadata["datetime"].replace(
            tzinfo=None
        ) - datetime.datetime.now(_LOCAL_TZ).replace(tzinfo=None)
        if "use_time" not in config or not config["use_time"]:
            config["datetime offset"] = datetime.timedelta(
                days=config["datetime offset"].days
            )
