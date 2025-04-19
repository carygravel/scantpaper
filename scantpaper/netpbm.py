"methods to deal with NetPBM files"

import math
import re

BINARY_BITMAP = 4
BINARY_GRAYMAP = 5
BITS_PER_BYTE = 8
BITMAP_BYTES_PER_PIXEL = 1 / BITS_PER_BYTE
GRAYMAP_CHANNELS = 1
PIXMAP_CHANNELS = 3


def file_size_from_header(filename):
    "Return file size expected by PNM header"
    header = read_header(filename)
    if header is None:
        return 0
    (magic_value, width, height, bytes_per_channel, header) = header
    padded_width = width
    if magic_value == BINARY_BITMAP:
        mod = padded_width % BITS_PER_BYTE
        if mod > 0:
            padded_width += BITS_PER_BYTE - mod

    datasize = (
        padded_width
        * height
        * bytes_per_channel
        * (
            BITMAP_BYTES_PER_PIXEL
            if magic_value == BINARY_BITMAP
            else (
                GRAYMAP_CHANNELS if magic_value == BINARY_GRAYMAP else PIXMAP_CHANNELS
            )
        )
    )
    return int(header + datasize), width, height


def read_header(filename):
    "return import metadata from header"
    with open(filename, mode="rb") as fhd:
        header = fhd.readline().decode("ascii")
        (magic_value, width, height, line) = (None, None, None, None)
        bytes_per_channel = 1
        regex = re.search(r"^P(\d)\n", header, re.MULTILINE | re.DOTALL | re.VERBOSE)
        if (header is not None) and regex:
            magic_value = int(regex.group(1))
        else:
            return None

        if magic_value < BINARY_BITMAP:
            return None

        for line in fhd:
            line = line.decode("ascii")
            header += line
            if re.search(r"^(\#|\s*\n)", line, re.MULTILINE | re.DOTALL | re.VERBOSE):
                continue
            regex = re.search(
                r"(\d*)[ ](\d*)\n", line, re.MULTILINE | re.DOTALL | re.VERBOSE
            )
            regex2 = re.search(r"(\d+)\n", line, re.MULTILINE | re.DOTALL | re.VERBOSE)
            if regex:
                (width, height) = (int(regex.group(1)), int(regex.group(2)))
                if magic_value == BINARY_BITMAP:
                    break

            elif magic_value > BINARY_BITMAP and regex2:
                maxval = int(regex2.group(1))
                bytes_per_channel = math.log(maxval + 1) / math.log(2) / BITS_PER_BYTE
                break

            else:
                return None
        return magic_value, width, height, bytes_per_channel, len(header)
