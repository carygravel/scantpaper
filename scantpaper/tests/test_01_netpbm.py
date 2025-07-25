"tests for NetPBM"

import os
import subprocess
import re
import tempfile
import netpbm


def test_1():
    "tests for NetPBM"
    for suffix in ["pbm", "pgm", "ppm"]:
        for depth in (8, 16):
            for size in ("8x5", "9x6"):
                width, height = None, None
                regex = re.search(r"(\d)x(\d)", size)
                if regex:
                    width, height = int(regex.group(1)), int(regex.group(2))

                with tempfile.NamedTemporaryFile(suffix=f".{suffix}") as file:
                    ftype = suffix.upper()
                    if ftype == "PBM":
                        cmd = [
                            "pnmdepth",
                            "-pbm",
                            "-depth",
                            str(depth),
                            "-width",
                            str(width),
                            "-height",
                            str(height),
                            file.name,
                        ]
                    elif ftype == "PGM":
                        cmd = [
                            "pnmdepth",
                            "-pgm",
                            "-depth",
                            str(depth),
                            "-width",
                            str(width),
                            "-height",
                            str(height),
                            file.name,
                        ]
                    elif ftype == "PPM":
                        cmd = [
                            "pnmdepth",
                            "-ppm",
                            "-depth",
                            str(depth),
                            "-width",
                            str(width),
                            "-height",
                            str(height),
                            file.name,
                        ]
                    subprocess.run(
                        [
                            "convert",
                            "-depth",
                            str(depth),
                            "-resize",
                            str(size),
                            "rose:",
                            file.name,
                        ],
                        check=True,
                    )
                    assert netpbm.file_size_from_header(file.name) == (
                        os.path.getsize(file.name),
                        width,
                        height,
                    ), f"get_size_from_PNM {ftype} {size} depth {depth}"

    #########################

    with tempfile.NamedTemporaryFile(suffix=".pnm") as file:
        assert netpbm.file_size_from_header(file.name) == os.path.getsize(
            file.name
        ), "0-length PNM"
