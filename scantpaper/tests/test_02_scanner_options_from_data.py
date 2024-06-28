"options from data"
from scanner.options import Options, Option
from frontend import enums


def test_1():
    "options from data"
    data = [
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
            index=1,
            cap=0,
            unit="0",
            size=0,
            desc="",
            name="",
            title="Geometry",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            index=2,
            cap="5",
            size=1,
            name="tl-x",
            unit="3",
            desc="Top-left x position of scan area.",
            constraint=(0, 200, 1),
            title="Top-left x",
            type="2",
        ),
        Option(
            index=3,
            cap="5",
            size=1,
            name="tl-y",
            unit="3",
            desc="Top-left y position of scan area.",
            constraint=(0, 200, 1),
            title="Top-left y",
            type="2",
        ),
        Option(
            index=4,
            cap="5",
            size=1,
            name="br-x",
            unit="3",
            desc="Bottom-right x position of scan area.",
            constraint=(0, 200, 1),
            title="Bottom-right x",
            type="2",
        ),
        Option(
            index=5,
            cap="5",
            size=1,
            name="br-y",
            unit="3",
            desc="Bottom-right y position of scan area.",
            constraint=(0, 200, 1),
            title="Bottom-right y",
            type="2",
        ),
        Option(
            index=6,
            cap="5",
            size=1,
            name="page-width",
            unit="3",
            desc="Specifies the width of the media.  Required for automatic "
            "centering of sheet-fed scans.",
            constraint=(0, 300, 1),
            title="Page width",
            type="2",
        ),
        Option(
            index=7,
            cap="5",
            size=1,
            name="page-height",
            unit="3",
            desc="Specifies the height of the media.",
            constraint=(0, 300, 1),
            title="Page height",
            type="2",
        ),
    ]
    options = Options(data)
    that = [
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
            index=1,
            cap=0,
            unit="0",
            size=0,
            desc="",
            name="",
            title="Geometry",
            type=enums.TYPE_GROUP,
            constraint=None,
        ),
        Option(
            index=2,
            cap="5",
            size=1,
            name="tl-x",
            unit="3",
            desc="Top-left x position of scan area.",
            constraint=(0, 200, 1),
            title="Top-left x",
            type="2",
        ),
        Option(
            index=3,
            cap="5",
            size=1,
            name="tl-y",
            unit="3",
            desc="Top-left y position of scan area.",
            constraint=(0, 200, 1),
            title="Top-left y",
            type="2",
        ),
        Option(
            index=4,
            cap="5",
            size=1,
            name="br-x",
            unit="3",
            desc="Bottom-right x position of scan area.",
            constraint=(0, 200, 1),
            title="Bottom-right x",
            type="2",
        ),
        Option(
            index=5,
            cap="5",
            size=1,
            name="br-y",
            unit="3",
            desc="Bottom-right y position of scan area.",
            constraint=(0, 200, 1),
            title="Bottom-right y",
            type="2",
        ),
        Option(
            index=6,
            cap="5",
            size=1,
            name="page-width",
            unit="3",
            desc="Specifies the width of the media.  Required for automatic "
            "centering of sheet-fed scans.",
            constraint=(0, 300, 1),
            title="Page width",
            type="2",
        ),
        Option(
            index=7,
            cap="5",
            size=1,
            name="page-height",
            unit="3",
            desc="Specifies the height of the media.",
            constraint=(0, 300, 1),
            title="Page height",
            type="2",
        ),
    ]
    assert options.array == that, "from data"

    assert options.supports_paper(
        {
            "x": 210,
            "y": 297,
            "l": 0,
            "t": 0,
        },
        0,
    ), "page-width supports_paper"
    assert options.supports_paper(
        {
            "x": 210,
            "y": 301,
            "l": 0,
            "t": 0,
        },
        1,
    ), "supports_paper with tolerance"
    assert not options.supports_paper(
        {
            "x": 210,
            "y": 297,
            "l": 0,
            "t": -10,
        },
        0,
    ), "page-width paper crosses top border"
    assert not options.supports_paper(
        {
            "x": 210,
            "y": 297,
            "l": 0,
            "t": 600,
        },
        0,
    ), "page-width paper crosses bottom border"
    assert not options.supports_paper(
        {
            "x": 210,
            "y": 297,
            "l": -10,
            "t": 0,
        },
        0,
    ), "page-width paper crosses left border"
    assert not options.supports_paper(
        {
            "x": 210,
            "y": 297,
            "l": 100,
            "t": 0,
        },
        0,
    ), "page-width paper crosses right border"
    assert not options.supports_paper(
        {
            "x": 301,
            "y": 297,
            "l": 0,
            "t": 0,
        },
        0,
    ), "page-width paper too wide"
    assert not options.supports_paper(
        {
            "x": 210,
            "y": 870,
            "l": 0,
            "t": 0,
        },
        0,
    ), "page-width paper too tall"

    options.delete_by_name("page-width")
    options.delete_by_name("page-height")
    del options.geometry["w"]
    del options.geometry["h"]

    assert options.supports_paper(
        {
            "x": 200,
            "y": 200,
            "l": 0,
            "t": 0,
        },
        0,
    ), "supports_paper"
    assert not options.supports_paper(
        {
            "x": 200,
            "y": 200,
            "l": 0,
            "t": -10,
        },
        0,
    ), "paper crosses top border"
    assert not options.supports_paper(
        {
            "x": 200,
            "y": 200,
            "l": 0,
            "t": 600,
        },
        0,
    ), "paper crosses bottom border"
    assert not options.supports_paper(
        {
            "x": 200,
            "y": 200,
            "l": -10,
            "t": 0,
        },
        0,
    ), "paper crosses left border"
    assert not options.supports_paper(
        {
            "x": 200,
            "y": 200,
            "l": 100,
            "t": 0,
        },
        0,
    ), "paper crosses right border"
    assert not options.supports_paper(
        {
            "x": 201,
            "y": 200,
            "l": 0,
            "t": 0,
        },
        0,
    ), "paper too wide"
    assert not options.supports_paper(
        {
            "x": 200,
            "y": 270,
            "l": 0,
            "t": 0,
        },
        0,
    ), "paper too tall"

    assert options.by_name("page-height") is None, "by name undefined"

    data = [
        Option(
            name="mode-group",
            desc="",
            cap=0,
            index=1,
            type=5,
            title="Scan mode",
            size=0,
            unit=0,
            constraint=None,
        ),
        Option(
            desc="Selects the scan mode (e.g., lineart, monochrome, or color).",
            index=2,
            constraint=["Lineart", "Gray", "Color"],
            type=3,
            title="Scan mode",
            unit=0,
            size=1,
            name="mode",
            cap=5,
        ),
        Option(
            size=1,
            unit=4,
            title="Scan resolution",
            type=1,
            index=3,
            desc="Sets the resolution of the scanned image.",
            constraint=[75, 100, 150, 200, 300],
            cap=5,
            name="resolution",
        ),
        Option(
            name="source",
            cap=5,
            type=3,
            constraint=["Flatbed", "ADF", "Duplex"],
            index=4,
            desc="Selects the scan source (such as a document-feeder).",
            size=1,
            unit=0,
            title="Scan source",
        ),
        Option(
            cap=64,
            name="advanced-group",
            unit=0,
            size=0,
            title="Advanced",
            type=5,
            index=5,
            desc="",
            constraint=None,
        ),
        Option(
            type=1,
            index=6,
            desc="Controls the brightness of the acquired image.",
            constraint=(-1000, 1000, 0),
            size=1,
            unit=0,
            title="Brightness",
            name="brightness",
            cap=69,
        ),
        Option(
            cap=69,
            name="contrast",
            title="Contrast",
            unit=0,
            size=1,
            index=7,
            desc="Controls the contrast of the acquired image.",
            constraint=(-1000, 1000, 0),
            type=1,
        ),
        Option(
            desc="Selects the scanner compression method for faster scans, "
            "possibly at the expense of image quality.",
            index=8,
            constraint=["None", "JPEG"],
            type=3,
            title="Compression",
            size=1,
            unit=0,
            name="compression",
            cap=69,
        ),
        Option(
            name="jpeg-quality",
            cap=101,
            type=1,
            index=9,
            desc="Sets the scanner JPEG compression factor. Larger numbers mean "
            "better compression, and smaller numbers mean better image quality.",
            constraint=(0, 100, 0),
            unit=0,
            size=1,
            title="JPEG compression factor",
        ),
        Option(
            cap=64,
            name="geometry-group",
            unit=0,
            size=0,
            title="Geometry",
            type=5,
            index=10,
            desc="",
            constraint=None,
        ),
        Option(
            name="tl-x",
            cap=5,
            type=2,
            desc="Top-left x position of scan area.",
            index=11,
            constraint=(0, 215.899993896484, 0),
            unit=3,
            size=1,
            title="Top-left x",
        ),
        Option(
            name="tl-y",
            cap=5,
            type=2,
            desc="Top-left y position of scan area.",
            index=12,
            constraint=(0, 381, 0),
            size=1,
            unit=3,
            title="Top-left y",
        ),
        Option(
            cap=5,
            name="br-x",
            size=1,
            unit=3,
            title="Bottom-right x",
            type=2,
            index=13,
            desc="Bottom-right x position of scan area.",
            constraint=(0, 215.899993896484, 0),
        ),
        Option(
            cap=5,
            name="br-y",
            title="Bottom-right y",
            unit=3,
            size=1,
            desc="Bottom-right y position of scan area.",
            index=14,
            constraint=(0, 381, 0),
            type=2,
        ),
    ]
    options = Options(data)
    assert options.supports_paper(
        {"t": 0, "l": 0, "y": 356, "x": 216}, 2
    ), "supports_paper with tolerance 2"
