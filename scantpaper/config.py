"helper functions to read and write config"

import os
import json
import logging
from types import SimpleNamespace
import datetime
from helpers import slurp
from const import SELECTORDRAGGER_TOOL
from i18n import _
from gi.repository import Gdk

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
    "text_position": "behind",
    "pdf font": None,
    "quality": 75,
    "image type": None,
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
    "threshold tool": 80,
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
logger = logging.getLogger(__name__)


def read_config(filename):
    "read the config"
    config = {}
    logger.info("Reading config from %s", filename)
    if not os.access(filename, os.R_OK):
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write("")

    configstr = slurp(filename)
    if len(configstr) > 0:
        try:
            config = json.loads(configstr)
        except json.decoder.JSONDecodeError:
            logger.error(
                "Error: unable to load settings.\nBacking up settings\nReverting to defaults"
            )
            os.rename(filename, f"{filename}.old")

    if "user_defined_tools" in config and not isinstance(
        config["user_defined_tools"], list
    ):
        config["user_defined_tools"] = [config["user_defined_tools"]]

    # deserialise device list
    if (
        "device list" in config
        and len(config["device list"]) > 0
        and isinstance(config["device list"][0], dict)
    ):
        config["device list"] = [SimpleNamespace(**x) for x in config["device list"]]

    # remove undefined profiles
    if "profile" in config:
        for profile in list(config["profile"].keys()):
            if not config["profile"][profile]:
                del config["profile"][profile]

    # deserialise timedelta
    if "datetime offset" in config:
        config["datetime offset"] = datetime.timedelta(
            days=config["datetime offset"][0],
            hours=config["datetime offset"][1],
            minutes=config["datetime offset"][2],
            seconds=config["datetime offset"][3],
        )

    # deserialise selection
    if "selection" in config and config["selection"] is not None:
        selection = Gdk.Rectangle()
        selection.x, selection.y, selection.width, selection.height = (
            config["selection"]["x"],
            config["selection"]["y"],
            config["selection"]["width"],
            config["selection"]["height"],
        )
        config["selection"] = selection

    for k in "image_control_tool", "viewer_tools":
        if k in config and isinstance(config[k], int):
            del config[k]

    logger.debug(config)
    return config


def _hash_profile_to_array(profile_hashref):
    """If the profile is a hash, the order is undefined.
    Sort it to be consistent for tests.
    """
    clone = []
    for key in sorted(profile_hashref.keys()):
        clone.append({key: profile_hashref[key]})

    return clone


def add_defaults(config):
    "add defaults"

    # remove unused settings
    for k in list(config.keys()):
        if k not in DEFAULTS:
            del config[k]

    # add default settings
    for k, v in DEFAULTS.items():
        if k not in config:
            config[k] = v


def remove_invalid_paper(hashref):
    "remove invalid paper formats"
    for paper in list(hashref.keys()):
        if paper in ["<>", "</>"]:
            del hashref[paper]
        else:
            for opt in ["x", "y", "t", "l"]:
                if not isinstance(hashref[paper], dict) or opt not in hashref[paper]:
                    del hashref[paper]
                    break


def write_config(rc, config):
    "write config"

    # serialise device list
    if "device list" in config:
        dl = []
        for dns in config["device list"]:
            d = {}
            for key in ["name", "vendor", "model", "label"]:
                if hasattr(dns, key):
                    d[key] = getattr(dns, key)
            dl.append(d)
        config["device list"] = dl

    # serialise timedelta
    if "datetime offset" in config:
        config["datetime offset"] = [
            config["datetime offset"].days,
            config["datetime offset"].seconds // 3600,
            (config["datetime offset"].seconds // 60) % 60,
            config["datetime offset"].seconds % 60,
        ]

    # serialise selection
    if "selection" in config and config["selection"] is not None:
        selection = {}
        selection["x"], selection["y"], selection["width"], selection["height"] = (
            config["selection"].x,
            config["selection"].y,
            config["selection"].width,
            config["selection"].height,
        )
        config["selection"] = selection

    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(config, sort_keys=True, indent=4))
    logger.info("Wrote config to %s", rc)


def update_config_from_imported_metadata(config, metadata):
    "update config from imported metadata"
    for name in ["author", "title", "subject", "keywords"]:
        if name in metadata:
            config[name] = metadata[name]
    if "datetime" in metadata and metadata["datetime"] is not None:
        config["datetime offset"] = (
            metadata["datetime"].replace(tzinfo=None) - datetime.datetime.now()
        )
        if "use_time" not in config or not config["use_time"]:
            config["datetime offset"] = datetime.timedelta(
                days=config["datetime offset"].days
            )
