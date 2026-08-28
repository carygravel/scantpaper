"Tests for scanner option handling"

import pytest
from frontend import enums
from scanner.options import Option, Options, within_tolerance


def test_within_tolerance():
    "test within_tolerance branches"
    options = Options(
        [
            Option(
                index=0,
                name="",
                title="Number of options",
                desc="Read-only option that specifies how many options a specific device supports.",
                type=enums.TYPE_INT,
                unit=enums.UNIT_NONE,
                size=4,
                cap=4,
                constraint=None,
            ),
            Option(
                index=1,
                name="",
                title="Group",
                desc="",
                type=enums.TYPE_GROUP,
                unit=enums.UNIT_NONE,
                size=0,
                cap=0,
                constraint=None,
            ),
            Option(
                index=2,
                name="mode",
                title="Mode",
                desc="Selects the scan mode.",
                type=enums.TYPE_STRING,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=["Gray", "Color"],
            ),
            Option(
                index=3,
                name="depth",
                title="Depth",
                desc="Number of bits per sample.",
                type=enums.TYPE_INT,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=[1, 8, 16],
            ),
            Option(
                index=4,
                name="hand-scanner",
                title="Hand scanner",
                desc="Simulate a hand-scanner.",
                type=enums.TYPE_BOOL,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=None,
            ),
            Option(
                index=7,
                name="resolution",
                title="Resolution",
                desc="Sets the resolution of the scanned image.",
                type=enums.TYPE_INT,
                unit=enums.UNIT_DPI,
                size=1,
                cap=5,
                constraint=(1, 1200, 1),
            ),
            Option(
                index=36,
                name="int",
                title="Int",
                desc="Int test option with no unit and no constraint set.",
                type=enums.TYPE_INT,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=None,
            ),
            Option(
                index=43,
                name="fixed",
                title="Fixed",
                desc="Fixed test option with no unit and no constraint set.",
                type=enums.TYPE_FIXED,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=None,
            ),
            Option(
                index=47,
                name="string",
                title="String",
                desc="String test option without constraint.",
                type=enums.TYPE_STRING,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=None,
            ),
        ]
    )

    assert not within_tolerance(
        options.array[1], "value", "value"
    ), "SANE_CONSTRAINT_NONE"
    assert within_tolerance(
        options.by_name("mode"), "Gray", "Gray"
    ), "SANE_CONSTRAINT_STRING_LIST positive"
    assert within_tolerance(
        options.by_name("depth"), 8, 8
    ), "SANE_CONSTRAINT_WORD_LIST positive"
    assert within_tolerance(
        options.by_name("resolution"), 50, 50
    ), "SANE_CONSTRAINT_RANGE exact"
    assert within_tolerance(
        options.by_name("resolution"), 50, 50.1
    ), "SANE_CONSTRAINT_RANGE inexact"
    assert not within_tolerance(
        options.by_name("mode"), "Gray", "gray"
    ), "SANE_CONSTRAINT_STRING_LIST negative"
    assert not within_tolerance(
        options.by_name("depth"), 8, 7
    ), "SANE_CONSTRAINT_WORD_LIST negative"
    assert not within_tolerance(
        options.by_name("resolution"), 50, 51.1
    ), "SANE_CONSTRAINT_RANGE negative"
    assert not within_tolerance(
        options.by_name("hand-scanner"), False, 1
    ), "SANE_TYPE_BOOL negative"
    assert within_tolerance(options.by_name("int"), 20, 20), "SANE_TYPE_INT positive"
    assert not within_tolerance(
        options.by_name("int"), 20, 21
    ), "SANE_TYPE_INT negative"
    assert within_tolerance(
        options.by_name("fixed"), 20.5, 20.5
    ), "SANE_TYPE_FIXED positive"
    assert not within_tolerance(
        options.by_name("fixed"), 20.0, 21
    ), "SANE_TYPE_FIXED negative"
    assert within_tolerance(
        options.by_name("string"), "20.5", "20.5"
    ), "SANE_TYPE_STRING positive"
    assert not within_tolerance(
        options.by_name("string"), "20.5", "21"
    ), "SANE_TYPE_STRING negative"

    option = Option(
        cap=enums.CAP_SOFT_SELECT + enums.CAP_SOFT_DETECT,
        constraint=(297.179992675781, 0.0, 0.0),
        desc="Top Left Y",
        index=14,
        size=1,
        name="tl-y",
        title="Top Left Y",
        type=enums.TYPE_FIXED,
        unit=enums.UNIT_MM,
    )
    assert within_tolerance(
        option, 0.999984741210938, 1, 0.001
    ), "SANE_CONSTRAINT_RANGE inexact with tolerance"


@pytest.mark.parametrize(
    ("options", "exception"),
    [(None, ValueError), ("", TypeError)],
)
def test_options_constructor_errors(options, exception):
    "test that Options raises an error on invalid input"
    with pytest.raises(exception):
        Options(options)


def test_can_duplex():
    "test can_duplex from the option name"
    options = Options(
        [
            Option(
                index=1,
                name="enable-duplex",
                title="Enable duplex",
                desc="Enables duplex scanning.",
                type=enums.TYPE_BOOL,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=None,
            )
        ]
    )
    assert options.can_duplex()

    options = Options(
        [
            Option(
                index=1,
                name="enable-duplex",
                title="Enable duplex",
                desc="Enables duplex scanning.",
                type=enums.TYPE_BOOL,
                unit=enums.UNIT_NONE,
                size=1,
                cap=enums.CAP_INACTIVE,
                constraint=None,
            )
        ]
    )
    assert not options.can_duplex(), "inactive option"

    options = Options(
        [
            Option(
                index=1,
                name="mode",
                title="Mode",
                desc="Selects the scan mode.",
                type=enums.TYPE_STRING,
                unit=enums.UNIT_NONE,
                size=1,
                cap=5,
                constraint=["Gray", "Color"],
            )
        ]
    )
    assert not options.can_duplex(), "no duplex option"


def test_option_name_none(
    sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
):
    "test option.name=None"

    raw_options = [
        Option(
            index=0,
            name="",
            title="Number of options",
            desc="Read-only option that specifies how many options a specific device supports.",
            type=1,
            unit=0,
            size=4,
            cap=4,
            constraint=None,
        ),
        Option(
            type=3,
            size=1,
            name=None,
            constraint=["Flatbed", "ADF"],
            title="Scan source",
            desc="Selects the scan source (such as a document-feeder).",
            index=1,
            cap=5,
            unit=0,
        ),
    ]

    options = Options(raw_options)
    assert options.source is None
