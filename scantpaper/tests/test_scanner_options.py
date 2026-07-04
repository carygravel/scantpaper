from scanner.options import Option, Options


def test_option_name_none(
    mocker, sane_scan_dialog, set_device_wait_reload, mainloop_with_timeout
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
