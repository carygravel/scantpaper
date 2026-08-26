"test config helper functions"

import os
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

from config import (
    DEFAULTS,
    _get_convert_command,
    add_defaults,
    read_config,
    remove_invalid_paper,
    update_config_from_imported_metadata,
    write_config,
)
from gi.repository import Gdk
from helpers import slurp

_LOCAL_TZ = datetime.now().astimezone().tzinfo


class MockedDateTime(datetime):
    "mock now"

    @classmethod
    def now(cls, tz=None):
        return datetime(2018, 1, 1, 0, 0, 0, tzinfo=tz)


def test_config():
    "test config helper functions"
    rc = "test"

    #########################

    config = """{
    "version": "1.3.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)
    example = {"version": "1.3.3"}
    output = read_config(rc)
    assert output == example, "Read JSON"

    #########################

    write_config(rc, example)

    example = config.split("\n")
    output = slurp(rc).split("\n")

    assert output == example, "Write JSON"

    #########################

    output = {"version": "1.3.3"}
    output["non-existant-option"] = None
    add_defaults(output)
    example = DEFAULTS.copy()
    example["version"] = "1.3.3"
    example["viewer_tools"] = "tabbed"
    assert output == example, "add_defaults"

    #########################

    output = {"Paper": {1: ["stuff"]}}
    remove_invalid_paper(output["Paper"])
    example = {"Paper": {}}
    assert output == example, "remove_invalid_paper (contents)"

    #########################

    output = {
        "Paper": {
            "<>": {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            }
        }
    }
    remove_invalid_paper(output["Paper"])
    example = {"Paper": {}}
    assert output == example, "remove_invalid_paper (name)"

    #########################

    config = """{
   "user_defined_tools" : "gimp %i"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {"user_defined_tools": ["gimp %i"]}
    output = read_config(rc)

    assert output == example, "force user_defined_tools to be an array"

    #########################

    config = """{
   "profile" : {
      "crash" : null
   },
   "version" : "1.7.3"
}
"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {"profile": {}, "version": "1.7.3"}
    output = read_config(rc)

    assert output == example, "remove undefined profiles"


def test_config_string_conversion():
    "test that old integer-based settings are converted to strings"
    rc = "test_string_conversion"

    config = """{
    "image_control_tool": 1,
    "viewer_tools": 2
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    output = read_config(rc)
    add_defaults(output)

    assert isinstance(
        output["image_control_tool"], str
    ), "image_control_tool should be a string"
    assert isinstance(output["viewer_tools"], str), "viewer_tools should be a string"

    os.remove(rc)


def test_config2(mocker):
    "test config helper functions"
    rc = "test"

    #########################

    config = """{
    "device list": [
        {
            "label": "test_label",
            "model": "test_model",
            "name": "test_name",
            "vendor": "test_vendor"
        }
    ],
    "version": "1.7.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {
        "device list": [
            SimpleNamespace(
                name="test_name",
                vendor="test_vendor",
                model="test_model",
                label="test_label",
            )
        ],
        "version": "1.7.3",
    }
    output = read_config(rc)

    assert output == example, "Deserialise device list"

    #########################

    write_config(rc, example)
    output = slurp(rc)
    assert output == config, "Serialise device list"

    #########################

    config = """{
    "datetime offset": [
        0,
        0,
        0,
        0
    ],
    "version": "1.7.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)
    example = {"version": "1.7.3", "datetime offset": timedelta(seconds=0)}
    output = read_config(rc)
    assert output == example, "Deserialise datetime offset"

    #########################

    write_config(rc, example)

    example = config.split("\n")
    output = slurp(rc).split("\n")

    assert output == example, "Serialise datetime offset"

    #########################

    mocker.patch("config.datetime.datetime", MockedDateTime)
    config = {"version": "1.7.3", "datetime offset": timedelta(seconds=0)}
    metadata = {
        "title": "title",
        "datetime": datetime(2017, 12, 31, 0, 0, 0, tzinfo=_LOCAL_TZ),
    }
    update_config_from_imported_metadata(config, metadata)
    example = {
        "datetime offset": timedelta(days=-1),
        "title": "title",
        "version": "1.7.3",
    }
    assert config == example, "update_config_from_imported_metadata"

    #########################

    config = """{
    "selection": {
        "height": 4,
        "width": 3,
        "x": 1,
        "y": 2
    },
    "version": "1.7.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 1, 2, 3, 4
    example = {"version": "1.7.3", "selection": selection}
    output = read_config(rc)
    assert output["selection"].x == 1, "Deserialise selection x"
    assert output["selection"].y == 2, "Deserialise selection y"
    assert output["selection"].width == 3, "Deserialise selection width"
    assert output["selection"].height == 4, "Deserialise selection height"

    #########################

    write_config(rc, example)

    example = config.split("\n")
    output = slurp(rc).split("\n")

    assert output == example, "Serialise selection"

    #########################

    config = """{
   "version" : "
}
"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    output = read_config(rc)

    assert output == {}, "deal with corrupt config"

    #########################

    os.remove(f"{rc}.old")  # rc doesn't exist because it was corrupt


def test_threshold_tool_migration():
    "test migration of threshold tool to the ink-strength scale"
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = os.path.join(tmpdirname, "config")

        # config predating the change: value migrated to 100 - v
        with open(rc, "w", encoding="utf-8") as fh:
            fh.write('{"version": "3.0.15", "threshold tool": 80}')
        output = read_config(rc)
        assert output["threshold tool"] == 20, "legacy value migrated"

        # config written by the change version is not migrated again
        with open(rc, "w", encoding="utf-8") as fh:
            fh.write('{"version": "3.0.16", "threshold tool": 20}')
        output = read_config(rc)
        assert output["threshold tool"] == 20, "current version not migrated"

        # config without a version is treated as legacy
        with open(rc, "w", encoding="utf-8") as fh:
            fh.write('{"threshold tool": 60}')
        output = read_config(rc)
        assert output["threshold tool"] == 40, "absent version treated as legacy"


def test_threshold_tool_default():
    "test that the default threshold tool value is 20"
    assert DEFAULTS["threshold tool"] == 20
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = os.path.join(tmpdirname, "config")
        output = read_config(rc)
        add_defaults(output)
        assert output["threshold tool"] == 20, "default threshold tool is 20"


def test_get_convert_command(mocker):
    "test _get_convert_command"
    mock_which = mocker.patch("config.shutil.which")

    # Test when 'magick' is available
    mock_which.side_effect = lambda x: "/usr/bin/magick" if x == "magick" else None
    assert _get_convert_command() == "magick"

    # Test when 'magick' is not available
    mock_which.side_effect = lambda x: None
    assert _get_convert_command() == "convert"


def test_read_non_existent_config():
    "test reading a config file that doesn't exist"
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = os.path.join(tmpdirname, "non_existent_config")
        output = read_config(rc)
        assert (
            output == {}
        ), "read_config should return empty dict for non-existent file"
        assert os.path.exists(
            rc
        ), "read_config should create the file if it doesn't exist"
