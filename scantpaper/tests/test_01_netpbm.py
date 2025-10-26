"tests for NetPBM"

import os
import subprocess
import re
import tempfile
import config
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
                    subprocess.run(
                        [
                            config.CONVERT_COMMAND,
                            "rose:",
                            "-depth",
                            str(depth),
                            "-resize",
                            str(size),
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
