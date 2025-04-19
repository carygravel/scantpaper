"tests for NetPBM"

import os
import subprocess
import re
import netpbm


def test_1():
    "tests for NetPBM"
    for ftype in ["pbm", "pgm", "ppm"]:
        for depth in (8, 16):
            for size in ("8x5", "9x6"):
                (width, height) = (None, None)
                regex = re.search(r"(\d)x(\d)", size)
                if regex:
                    (width, height) = (int(regex.group(1)), int(regex.group(2)))

                file = f"test.{ftype}"
                subprocess.run(
                    [
                        "convert",
                        "-depth",
                        str(depth),
                        "-resize",
                        str(size),
                        "rose:",
                        str(file),
                    ],
                    check=True,
                )
                assert netpbm.file_size_from_header(file) == (
                    os.path.getsize(file),
                    width,
                    height,
                ), f"get_size_from_PNM {ftype} {size} depth {depth}"
                os.remove(file)

    #########################

    file = "test.pnm"
    subprocess.run(["touch", str(file)], check=True)
    assert netpbm.file_size_from_header(file) == (os.path.getsize(file)), "0-length PNM"
    os.remove(file)
