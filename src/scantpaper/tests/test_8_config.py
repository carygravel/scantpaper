"""test config helper functions."""

import pathlib
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

from gi.repository import Gdk

from scantpaper.config import (
    DEFAULTS,
    _coerce_bool,
    _coerce_float,
    _coerce_int,
    _coerce_str,
    _coerce_to_type,
    _get_convert_command,
    add_defaults,
    read_config,
    remove_invalid_paper,
    update_config_from_imported_metadata,
    write_config,
)
from scantpaper.helpers import slurp

_LOCAL_TZ = datetime.now().astimezone().tzinfo


class MockedDateTime(datetime):
    """mock now."""

    @classmethod
    def now(cls, tz=None):
        """Now."""
        return datetime(2018, 1, 1, 0, 0, 0, tzinfo=tz)


def test_config():
    """Test config helper functions."""
    rc = "test"

    #########################

    config = """{
    "version": "1.3.3"
}"""
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
        fh.write(config)
    example = {"version": "1.3.3"}
    output = read_config(rc)
    assert output == example, "Read JSON"
    assert output.load_warnings == [], "clean load reports no warnings"

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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
        fh.write(config)

    example = {"profile": {}, "version": "1.7.3"}
    output = read_config(rc)

    assert output == example, "remove undefined profiles"


def test_config_string_conversion():
    """Test that old integer-based settings are converted to strings."""
    rc = "test_string_conversion"

    config = """{
    "image_control_tool": 1,
    "viewer_tools": 2
}"""
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
        fh.write(config)

    output = read_config(rc)
    add_defaults(output)

    assert isinstance(output["image_control_tool"], str), (
        "image_control_tool should be a string"
    )
    assert isinstance(output["viewer_tools"], str), "viewer_tools should be a string"

    pathlib.Path(rc).unlink()


def test_config2(mocker):
    """Test config helper functions."""
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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
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

    mocker.patch("scantpaper.config.datetime.datetime", MockedDateTime)
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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
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
    with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
        fh.write(config)

    output = read_config(rc)

    assert output == {}, "deal with corrupt config"

    #########################

    pathlib.Path(f"{rc}.old").unlink()  # rc doesn't exist because it was corrupt


def test_threshold_tool_migration():
    """Test migration of threshold tool to the ink-strength scale."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "config"

        # config predating the change: value migrated to 100 - v
        with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
            fh.write('{"version": "3.0.15", "threshold tool": 80}')
        output = read_config(rc)
        assert output["threshold tool"] == 20, "legacy value migrated"

        # config written by the change version is not migrated again
        with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
            fh.write('{"version": "3.0.16", "threshold tool": 20}')
        output = read_config(rc)
        assert output["threshold tool"] == 20, "current version not migrated"

        # config without a version is treated as legacy
        with pathlib.Path(rc).open("w", encoding="utf-8") as fh:
            fh.write('{"threshold tool": 60}')
        output = read_config(rc)
        assert output["threshold tool"] == 40, "absent version treated as legacy"


def test_threshold_tool_default():
    """Test that the default threshold tool value is 20."""
    assert DEFAULTS["threshold tool"] == 20
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "config"
        output = read_config(rc)
        add_defaults(output)
        assert output["threshold tool"] == 20, "default threshold tool is 20"


def test_get_convert_command(mocker):
    """Test _get_convert_command."""
    mock_which = mocker.patch("scantpaper.config.shutil.which")

    # Test when 'magick' is available
    mock_which.side_effect = lambda x: "/usr/bin/magick" if x == "magick" else None
    assert _get_convert_command() == "magick"

    # Test when 'magick' is not available
    mock_which.side_effect = lambda _x: None
    assert _get_convert_command() == "convert"


def test_read_non_existent_config():
    """Test reading a config file that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "non_existent_config"
        output = read_config(rc)
        assert output == {}, (
            "read_config should return empty dict for non-existent file"
        )
        assert pathlib.Path(rc).exists(), (
            "read_config should create the file if it doesn't exist"
        )
        assert output.load_warnings == [], "no warnings for a missing file"


def test_rescue_config_from_unparseable_file():
    """An unparseable file rescues intact settings and keeps a backup."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        rc.write_text(
            "{\n"
            '  "rotate facing": 90,\n'
            '  "rotate reverse": 270,\n'
            '  "rotate facing": 180,\n'
            "  junk,\n"
            '  "not-a-settings-key": true,\n'
            '  "thumb panel": 100\n'
            "}\n",
            encoding="utf-8",
        )

        output = read_config(rc)

        assert output["rotate facing"] == 90, "first intact key rescued"
        assert output["rotate reverse"] == 270, "intact key rescued"
        assert output["thumb panel"] == 100, "keys after the junk line rescued"
        assert not rc.exists(), "broken file was renamed"
        assert pathlib.Path(f"{rc}.old").exists(), "backup kept"
        assert output.load_warnings, "a warning is reported"
        assert "rotate facing" in output.load_warnings[0], (
            "warning lists the rescued keys"
        )


def test_coerce_helpers():
    """The lossless coercion helpers cover every scalar type branch."""
    assert _coerce_bool(value=True) is True
    assert _coerce_bool(1) is True
    assert _coerce_bool(0) is False
    assert _coerce_bool("TRUE") is True
    assert _coerce_bool("0") is False
    assert _coerce_bool(2) is None

    assert _coerce_int(value=True) == 1
    assert _coerce_int(90.0) == 90
    assert _coerce_int(90.5) is None
    assert _coerce_int("7") == 7
    assert _coerce_int([1]) is None

    assert _coerce_float("0.05") == 0.05
    assert _coerce_float([1]) is None

    assert _coerce_str("x") == "x"
    assert _coerce_str(35) == "35"
    assert _coerce_str(0.5) == "0.5"
    assert _coerce_str(value=True) == "True"
    assert _coerce_str([1]) is None

    assert _coerce_to_type("5", int) == 5
    assert _coerce_to_type("0.05", float) == 0.05
    assert _coerce_to_type("none", str) == "none"
    assert _coerce_to_type("1", bool) is True
    assert _coerce_to_type(0, bool) is False
    assert _coerce_to_type(1, timedelta) is None, "unknown target type"


def test_wrong_typed_structural_settings_preserved():
    """Non-deserialisable structural values are kept raw with a warning."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        rc.write_text(
            "{"
            '"device list": "broken", "profile": "broken", '
            '"datetime offset": "broken", "selection": "broken"}',
            encoding="utf-8",
        )

        output = read_config(rc)

        assert output["device list"] == "broken"
        assert output["profile"] == "broken"
        assert output["datetime offset"] == "broken"
        assert output["selection"] == "broken"
        assert output.load_warnings, "wrong types record warnings"


def test_threshold_tool_wrong_type_not_migrated():
    """A non-integer threshold tool is left for normalisation, not migrated."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        rc.write_text('{"version": "3.0.15", "threshold tool": "80"}')
        output = read_config(rc)
        assert output["threshold tool"] == 80, "string coerced but not migrated"


def test_normalise_wrong_typed_scalar_settings():
    """Wrongly typed scalars are coerced; unusable values are kept with a warning."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        rc.write_text(
            '{"rotate facing": "270", "thumb panel": "garbage"}',
            encoding="utf-8",
        )

        output = read_config(rc)

        assert output["rotate facing"] == 270, "lossless coercion applied"
        assert output["thumb panel"] == "garbage", "unusable value kept raw"
        messages = output.load_warnings
        assert any("rotate facing" in message for message in messages), (
            "coercion records a warning"
        )
        assert any("thumb panel" in message for message in messages), (
            "raw value records a warning"
        )


def test_write_config_is_copied_and_never_writes_old():
    """write_config serialises on a copy and never writes to *.old."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = pathlib.Path(tmpdirname) / "scantpaperrc"
        settings = {
            "device list": [
                SimpleNamespace(
                    name="name", vendor="vendor", model="model", label="label"
                )
            ],
            "datetime offset": timedelta(seconds=60),
            "version": "1.7.3",
        }

        write_config(rc, settings)

        assert isinstance(settings["device list"][0], SimpleNamespace), (
            "caller's device list left deserialised"
        )
        assert isinstance(settings["datetime offset"], timedelta), (
            "caller's datetime offset left deserialised"
        )
        assert not pathlib.Path(f"{rc}.old").exists(), "never writes to *.old"

        output = read_config(rc)
        assert output["version"] == "1.7.3", "written file is still readable"
        assert output["device list"][0].name == "name", "device list round-trips"
        assert output["datetime offset"] == timedelta(seconds=60), (
            "datetime offset round-trips"
        )
