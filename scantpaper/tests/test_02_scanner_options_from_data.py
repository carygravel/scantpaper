"options from data"
from scanner.options import Options


def test_1():
    "options from data"
    data = [
        {
            "cap": "",
            "unit": "0",
            "max_values": 0,
            "desc": "",
            "name": "",
            "title": "Geometry",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "tl-x",
            "val": 0,
            "unit": "3",
            "desc": "Top-left x position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Top-left x",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "tl-y",
            "val": 0,
            "unit": "3",
            "desc": "Top-left y position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Top-left y",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "br-x",
            "val": 80,
            "unit": "3",
            "desc": "Bottom-right x position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Bottom-right x",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "br-y",
            "val": 100,
            "unit": "3",
            "desc": "Bottom-right y position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Bottom-right y",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "page-width",
            "val": 200,
            "unit": "3",
            "desc": "Specifies the width of the media.  Required for automatic centering of sheet-fed scans.",
            "constraint": {"min": 0, "max": 300, "quant": 1},
            "title": "Page width",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "cap": "5",
            "max_values": 1,
            "name": "page-height",
            "val": 200,
            "unit": "3",
            "desc": "Specifies the height of the media.",
            "constraint": {"min": 0, "max": 300, "quant": 1},
            "title": "Page height",
            "type": "2",
            "constraint_type": "1",
        },
    ]
    options = Options(data)
    that = [
        {
            "index": 0,
            "cap": "",
            "unit": "0",
            "max_values": 0,
            "desc": "",
            "name": "",
            "title": "Geometry",
            "type": "TYPE_GROUP",
            "constraint_type": "CONSTRAINT_NONE",
        },
        {
            "index": 1,
            "cap": "5",
            "max_values": 1,
            "name": "tl-x",
            "val": 0,
            "unit": "3",
            "desc": "Top-left x position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Top-left x",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "index": 2,
            "cap": "5",
            "max_values": 1,
            "name": "tl-y",
            "val": 0,
            "unit": "3",
            "desc": "Top-left y position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Top-left y",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "index": 3,
            "cap": "5",
            "max_values": 1,
            "name": "br-x",
            "val": 80,
            "unit": "3",
            "desc": "Bottom-right x position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Bottom-right x",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "index": 4,
            "cap": "5",
            "max_values": 1,
            "name": "br-y",
            "val": 100,
            "unit": "3",
            "desc": "Bottom-right y position of scan area.",
            "constraint": {"min": 0, "max": 200, "quant": 1},
            "title": "Bottom-right y",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "index": 5,
            "cap": "5",
            "max_values": 1,
            "name": "page-width",
            "val": 200,
            "unit": "3",
            "desc": "Specifies the width of the media.  Required for automatic centering of sheet-fed scans.",
            "constraint": {"min": 0, "max": 300, "quant": 1},
            "title": "Page width",
            "type": "2",
            "constraint_type": "1",
        },
        {
            "index": 6,
            "cap": "5",
            "max_values": 1,
            "name": "page-height",
            "val": 200,
            "unit": "3",
            "desc": "Specifies the height of the media.",
            "constraint": {"min": 0, "max": 300, "quant": 1},
            "title": "Page height",
            "type": "2",
            "constraint_type": "1",
        },
    ]
    assert options.array == that, "from data"

    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 1
    ), "page-width supports_paper"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 301,
                "l": 0,
                "t": 0,
            },
            1,
        )
        == 1
    ), "supports_paper with tolerance"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": -10,
            },
            0,
        )
        == 0
    ), "page-width paper crosses top border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 600,
            },
            0,
        )
        == 0
    ), "page-width paper crosses bottom border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": -10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper crosses left border"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 297,
                "l": 100,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper crosses right border"
    assert (
        options.supports_paper(
            {
                "x": 301,
                "y": 297,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper too wide"
    assert (
        options.supports_paper(
            {
                "x": 210,
                "y": 870,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "page-width paper too tall"

    options.delete_by_name("page-width")
    options.delete_by_name("page-height")
    del options.geometry["w"]
    del options.geometry["h"]

    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 200,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 1
    ), "supports_paper"
    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 200,
                "l": 0,
                "t": -10,
            },
            0,
        )
        == 0
    ), "paper crosses top border"
    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 200,
                "l": 0,
                "t": 600,
            },
            0,
        )
        == 0
    ), "paper crosses bottom border"
    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 200,
                "l": -10,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses left border"
    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 200,
                "l": 100,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper crosses right border"
    assert (
        options.supports_paper(
            {
                "x": 201,
                "y": 200,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper too wide"
    assert (
        options.supports_paper(
            {
                "x": 200,
                "y": 270,
                "l": 0,
                "t": 0,
            },
            0,
        )
        == 0
    ), "paper too tall"

    assert options.by_name("page-height") == None, "by name undefined"

    data = [
        {
            "constraint_type": 0,
            "name": "mode-group",
            "cap": 0,
            "index": 1,
            "type": 5,
            "title": "Scan mode",
            "max_values": 0,
            "unit": 0,
        },
        {
            "desc": "Selects the scan mode (e.g., lineart, monochrome, or color).",
            "index": 2,
            "constraint": ["Lineart", "Gray", "Color"],
            "type": 3,
            "title": "Scan mode",
            "val": "Gray",
            "unit": 0,
            "max_values": 1,
            "constraint_type": 3,
            "name": "mode",
            "cap": 5,
        },
        {
            "max_values": 1,
            "unit": 4,
            "title": "Scan resolution",
            "val": 300,
            "type": 1,
            "index": 3,
            "desc": "Sets the resolution of the scanned image.",
            "constraint": [75, 100, 150, 200, 300],
            "cap": 5,
            "name": "resolution",
            "constraint_type": 2,
        },
        {
            "name": "source",
            "constraint_type": 3,
            "cap": 5,
            "type": 3,
            "constraint": ["Flatbed", "ADF", "Duplex"],
            "index": 4,
            "desc": "Selects the scan source (such as a document-feeder).",
            "max_values": 1,
            "unit": 0,
            "title": "Scan source",
            "val": "ADF",
        },
        {
            "cap": 64,
            "name": "advanced-group",
            "constraint_type": 0,
            "unit": 0,
            "max_values": 0,
            "title": "Advanced",
            "type": 5,
            "index": 5,
        },
        {
            "type": 1,
            "index": 6,
            "desc": "Controls the brightness of the acquired image.",
            "constraint": {"min": -1000, "quant": 0, "max": 1000},
            "max_values": 1,
            "unit": 0,
            "title": "Brightness",
            "val": 0,
            "name": "brightness",
            "constraint_type": 1,
            "cap": 69,
        },
        {
            "cap": 69,
            "constraint_type": 1,
            "name": "contrast",
            "val": 0,
            "title": "Contrast",
            "unit": 0,
            "max_values": 1,
            "index": 7,
            "desc": "Controls the contrast of the acquired image.",
            "constraint": {"min": -1000, "quant": 0, "max": 1000},
            "type": 1,
        },
        {
            "desc": "Selects the scanner compression method for faster scans, possibly at the expense of image quality.",
            "index": 8,
            "constraint": ["None", "JPEG"],
            "type": 3,
            "title": "Compression",
            "val": "JPEG",
            "max_values": 1,
            "unit": 0,
            "constraint_type": 3,
            "name": "compression",
            "cap": 69,
        },
        {
            "name": "jpeg-quality",
            "constraint_type": 1,
            "cap": 101,
            "type": 1,
            "index": 9,
            "desc": "Sets the scanner JPEG compression factor. Larger numbers mean better compression, and smaller numbers mean better image quality.",
            "constraint": {"min": 0, "quant": 0, "max": 100},
            "unit": 0,
            "max_values": 1,
            "title": "JPEG compression factor",
        },
        {
            "cap": 64,
            "name": "geometry-group",
            "constraint_type": 0,
            "unit": 0,
            "max_values": 0,
            "title": "Geometry",
            "type": 5,
            "index": 10,
        },
        {
            "name": "tl-x",
            "constraint_type": 1,
            "cap": 5,
            "type": 2,
            "desc": "Top-left x position of scan area.",
            "index": 11,
            "constraint": {"quant": 0, "min": 0, "max": 215.899993896484},
            "unit": 3,
            "max_values": 1,
            "title": "Top-left x",
            "val": "0",
        },
        {
            "name": "tl-y",
            "constraint_type": 1,
            "cap": 5,
            "type": 2,
            "desc": "Top-left y position of scan area.",
            "index": 12,
            "constraint": {"quant": 0, "min": 0, "max": 381},
            "max_values": 1,
            "unit": 3,
            "title": "Top-left y",
            "val": "0",
        },
        {
            "cap": 5,
            "name": "br-x",
            "constraint_type": 1,
            "max_values": 1,
            "unit": 3,
            "title": "Bottom-right x",
            "val": 215.899993896484,
            "type": 2,
            "index": 13,
            "desc": "Bottom-right x position of scan area.",
            "constraint": {"quant": 0, "min": 0, "max": 215.899993896484},
        },
        {
            "cap": 5,
            "constraint_type": 1,
            "name": "br-y",
            "title": "Bottom-right y",
            "val": 381,
            "unit": 3,
            "max_values": 1,
            "desc": "Bottom-right y position of scan area.",
            "index": 14,
            "constraint": {"max": 381, "min": 0, "quant": 0},
            "type": 2,
        },
    ]
    options = Options(data)
    assert (
        options.supports_paper({"t": 0, "l": 0, "y": 356, "x": 216}, 1) == 1
    ), "supports_paper with tolerance 2"
