"Classes and methods for reading and writing the bounding box trees from HOCR files"
import re
from html.parser import HTMLParser
import json
from const import ANNOTATION_COLOR, POINTS_PER_INCH

DOUBLE_QUOTES = '"'
BBOX_REGEX = r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
HILITE_REGEX = r"[(]hilite\s+[#][A-Fa-f\d]{6}[)]\s+[(]xor[)]"
HALF = 0.5
VERSION = "2.13.2"
HOCR_HEADER = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>"""


def flatten_tree(oldbox, newtree):
    "refactor a nested tree into a list"
    # clone bbox without children
    newbox = dict(oldbox.items())
    if "contents" in newbox:
        del newbox["contents"]
    newtree.append(newbox)


class Bboxtree:
    "Read and write the bounding box trees from HOCR files"

    def __init__(self, json_string=None):
        self.bbox_tree = []
        if json_string is not None:
            self.bbox_tree = json.loads(json_string)

    def valid(self):
        "return whether the bboxes are valid"
        for bbox in self.get_bbox_iter():
            _x_1, _y_1, x_2, y_2 = bbox["bbox"]
            if bbox["type"] == "page":
                if x_2 == 0 or y_2 == 0:
                    return False
            return True
        return False

    def json(self):
        "seríalise the bboxtree object as JSON"
        return json.dumps(self.bbox_tree)

    def from_hocr(self, hocr):
        "write bboxtree to HOCR string"
        if (hocr is None) or not re.search(
            r"<body>[\s\S]*<\/body>", hocr, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            return
        box_tree = _hocr2boxes(hocr)
        _prune_empty_branches(box_tree)
        if len(box_tree) > 0:
            self.bbox_tree = []
            self._walk_bboxes(box_tree[0])

    def from_text(self, text, width, height):
        "create bboxtree from string"
        self.bbox_tree.append(
            {
                "type": "page",
                "bbox": [0, 0, width, height],
                "text": text,
                "depth": 0,
            }
        )

    def get_bbox_iter(self):
        """an iterator for parsing bboxes
        iterator returns bbox
        my $iter = $self->get_bbox_iter();
        while (my $bbox = $iter->()) {}"""
        for bbox in self.bbox_tree:
            yield bbox

    def to_djvu_txt(self):
        "write bboxtree to string for djvu text"
        string = ""
        prev_depth, height = None, None
        for bbox in self.get_bbox_iter():
            if prev_depth is not None:
                while prev_depth >= bbox["depth"]:
                    prev_depth -= 1
                    string += ")"

            prev_depth = bbox["depth"]
            bbox_type = bbox["type"]

            # deal with unsupported types, e.g. header
            if not re.search(
                r"^(?:page|column|para|line|word)$",
                bbox_type,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            ):
                regex = re.search(
                    r"([A-Za-z]+)", bbox["id"], re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                if regex:
                    bbox_type = regex.group(1)

                else:
                    bbox_type = "line"

            if bbox_type == "page":
                height = bbox["bbox"][-1]
            x_1, y_1, x_2, y_2 = bbox["bbox"]
            if bbox["depth"] != 0:
                string += "\n"
            string += " " * bbox["depth"] * 2
            string += f"({bbox_type} %d %d %d %d" % (
                x_1,
                height - y_2,
                x_2,
                height - y_1,
            )
            if "text" in bbox:
                string += (
                    " " + DOUBLE_QUOTES + _escape_text(bbox["text"]) + DOUBLE_QUOTES
                )

        if prev_depth is not None:
            while prev_depth >= 0:
                prev_depth -= 1
                string += ")"

        if string != "":
            string += "\n"
        return string

    def to_djvu_ann(self):
        "write bboxtree as string for djvu annotation layer"
        string = ""
        height = None
        for bbox in self.get_bbox_iter():
            if bbox["type"] == "page":
                height = bbox["bbox"][-1]
            if "text" in bbox:
                x_1, y_1, x_2, y_2 = bbox["bbox"]
                string += (
                    f'(maparea "" "{_escape_text(bbox["text"])}"'
                    f" (rect {x_1} {height - y_2} {x_2 - x_1} {y_2 - y_1})"
                    f" (hilite #{ANNOTATION_COLOR}) (xor))\n"
                )

        return string

    def from_djvu_ann(self, djvuann, imagew, imageh):
        "create bboxtree from djvu annotation layer"
        self.bbox_tree.append(
            {
                "type": "page",
                "bbox": [
                    0,
                    0,
                    imagew,
                    imageh,
                ],
                "depth": 0,
            }
        )
        for line in re.split(r"\n", djvuann):
            if line == "":
                continue
            regex = re.search(
                fr"""[(]maparea\s+\".*\" # url
\s+\"(.*)\" # text field enclosed in inverted commas
\s+[(]rect\s+{BBOX_REGEX}[)] # bounding box
\s+{HILITE_REGEX} # highlight color
[)]""",
                line,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                self.bbox_tree.append(
                    {
                        "type": "word",
                        "depth": 1,
                        "text": regex.group(1),
                        "bbox": [
                            int(regex.group(2)),
                            imageh - int(regex.group(3)) - int(regex.group(5)),
                            int(regex.group(2)) + int(regex.group(4)),
                            imageh - int(regex.group(3)),
                        ],
                    }
                )

            else:
                raise ValueError(f"Error parsing djvu annotation '{line}'")

    def to_text(self):
        "Escape backslashes and inverted commas, return as plain text"
        string = ""
        for bbox in self.get_bbox_iter():
            if string != "":
                if bbox["type"] == "para":
                    string += "\n\n"

            if "text" in bbox:
                string += bbox["text"] + " "

        # squash whitespace at the end of any line
        string = re.sub(
            r"[ ]+$", r"", string, flags=re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        return string

    def from_djvu_txt(self, djvutext):
        "create bboxtree from djvu text layer"
        height = None
        depth = 0
        for line in re.split(r"\n", djvutext):
            if line == "":
                continue
            regex = re.search(
                fr"^\s*([(]+)(\w+)\s+{BBOX_REGEX}(.*?)([)]*)$",
                line,
                re.MULTILINE | re.DOTALL | re.VERBOSE,
            )
            if regex:
                bbox = {}
                depth += len(regex.group(1))
                bbox["depth"] = depth - 1
                bbox["type"] = regex.group(2)
                if regex.group(2) == "page":
                    height = int(regex.group(6))
                bbox["bbox"] = [
                    int(regex.group(3)),
                    height - int(regex.group(6)),
                    int(regex.group(5)),
                    height - int(regex.group(4)),
                ]
                text = regex.group(7)
                if regex.group(8):
                    depth -= int(len(regex.group(8)))
                regex = re.search(
                    r'^\s*"(.*)"\s*\Z', text, re.MULTILINE | re.DOTALL | re.VERBOSE
                )
                if regex:
                    bbox["text"] = regex.group(1)

                self.bbox_tree.append(bbox)

            else:
                raise ValueError(f"Error parsing djvu line '{line}'")

    def from_pdftotext(self, html, resolution, image_size):
        "create bboxtree from PDF text layer"
        if not re.search(
            r"<body>[\s\S]*<\/body>", html, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            return
        box_tree = _pdftotext2boxes(html, resolution, image_size)
        _prune_empty_branches(box_tree)
        if box_tree:
            self._walk_bboxes(box_tree[0])

    def to_hocr(self):
        "write the bboxtree as an HOCR string"
        string = HOCR_HEADER + "\n"
        prev_depth, tags = None, []
        for bbox in self.get_bbox_iter():
            sub_string, prev_depth = _bbox_to_hocr(bbox, prev_depth, tags)
            string += sub_string

        string += "</" + (tags.pop() if tags else "") + ">\n"
        prev_depth -= 1
        while prev_depth >= 0:
            string += (
                " " * (2 + prev_depth) + "</" + (tags.pop() if tags else "") + ">\n"
            )
            prev_depth -= 1

        string += " </body>\n</html>\n"
        return string

    def crop(self, left, top, width, height):
        "crop bboxtree"
        i = 0
        while i < len(self.bbox_tree):
            bbox = self.bbox_tree[i]
            text_x1, text_y1, text_x2, text_y2 = bbox["bbox"]
            text_x1, text_x2 = _crop_axis(text_x1, text_x2, left, left + width)
            text_y1, text_y2 = _crop_axis(text_y1, text_y2, top, top + height)

            # cropped outside box, so remove box
            if (text_x1 is None) or (text_y1 is None):
                del self.bbox_tree[i]
                continue

            # update box
            bbox["bbox"] = [text_x1, text_y1, text_x2, text_y2]
            i += 1

        return self

    def _walk_bboxes(self, bbox, depth=0):
        "walk the tree, executing the callback on each bounding box"
        bbox["depth"] = depth
        depth += 1
        flatten_tree(bbox, self.bbox_tree)

        if "contents" in bbox:
            for child in bbox["contents"]:
                self._walk_bboxes(child, depth)


class HOCRParser(HTMLParser):
    "parser for HOCR string"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.boxes = []
        self.stack = []
        self.data = {}

    def handle_starttag(self, tag, attrs):
        token = dict(attrs)
        if "class" in token and "title" in token:
            self._parse_title(token["title"])
            self._parse_class(token["class"])

            # pick up previous pointer to add style
            if "type" not in self.data:
                self.data = self.stack[-1]

            if "type" not in self.data:
                return

            # put information xocr_word information in parent ocr_word
            if self.data["type"] == "word" and self.stack[-1]["type"] == "word":
                for key in self.data.keys():
                    if key not in self.stack[-1]:
                        self.stack[-1][key] = self.data[key]

                # pick up previous pointer to add any later text
                self.data = self.stack[-1]

            else:
                if "id" in token:
                    self.data["id"] = token["id"]

                # if we have previous data, add the new data to the
                # contents of the previous data point
                if self.stack and self.data != self.stack[-1] and "bbox" in self.data:
                    if "contents" not in self.stack[-1]:
                        self.stack[-1]["contents"] = []
                    self.stack[-1]["contents"].append(self.data)

        # pick up previous pointer
        # so that unknown tags don't break the chain
        elif self.stack:
            self.data = self.stack[-1]

        self._parse_style(tag)

        # put the new data point on the stack
        self.stack.append(self.data)

    def _parse_style(self, tag):
        if self.data:
            if tag in ["strong", "em"]:
                if "style" not in self.data:
                    self.data["style"] = []
                self.data["style"].append(tag)

    def _parse_title(self, title):
        data = {}

        regex = re.search(
            fr"\bbbox\s+{BBOX_REGEX}", title, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            if regex.group(1) != regex.group(3) and regex.group(2) != regex.group(4):
                data["bbox"] = [
                    int(regex.group(1)),
                    int(regex.group(2)),
                    int(regex.group(3)),
                    int(regex.group(4)),
                ]

        regex = re.search(
            r"\btextangle\s+(\d+)", title, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            data["textangle"] = int(regex.group(1))
        regex = re.search(
            r"\bx_wconf\s+(-?\d+)", title, re.MULTILINE | re.DOTALL | re.VERBOSE
        )
        if regex:
            data["confidence"] = int(regex.group(1))
        regex = re.search(
            r"\bbaseline\s+((?:-?\d+(?:[.]\d+)?\s+)*-?\d+)",
            title,
            re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        if regex:
            values = re.split(r"\s+", regex.group(1))
            for i, value in enumerate(values):
                if str(float(value)) == value:
                    values[i] = float(value)
                else:
                    values[i] = int(value)

            # make sure we at least have 2 coefficients
            if len(values) < 2:
                values.insert(0, 0)
            data["baseline"] = values

        self.data = data

    def _parse_class(self, class_name):
        class_name = re.split("_", class_name)
        if len(class_name) == 2:
            class_name[1] = (
                class_name[1].replace("carea", "column").replace("par", "para")
            )
            if class_name[1] in [
                "page",
                "header",
                "footer",
                "caption",
                "column",
                "para",
                "line",
                "word",
            ]:
                self.data["type"] = class_name[1]
                if class_name[1] == "page":
                    self.boxes.append(self.data)

    def handle_endtag(self, tag):
        self.data = self.stack.pop()

    def handle_data(self, data):
        data = data.rstrip()
        if data != "":
            self.data["text"] = data


def _hocr2boxes(hocr):

    parser = HOCRParser()
    parser.feed(hocr)
    return parser.boxes


def _prune_empty_branches(boxes):
    i = 0
    while i < len(boxes):
        child = boxes[i]
        if "contents" in child:
            _prune_empty_branches(child["contents"])
            if len(child["contents"]) == 0:
                del child["contents"]

        if len(boxes) > 0 and not ("contents" in child or "text" in child):
            del boxes[i]

        else:
            i += 1


def _escape_text(txt):

    txt = re.sub(r"\\", r"\\\\", txt, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)
    txt = re.sub(r"\"", r"\\\\\"", txt, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)
    return txt


class PDFTextParser(HTMLParser):
    "parser for HTML string for PDF text layer"

    def __init__(self, xresolution, yresolution, imagew, imageh, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.boxes = []
        self.stack = []
        self.data = {}
        self.resolution = (xresolution, yresolution)
        self.image_size = (imagew, imageh)
        self.offset = 0

    def handle_starttag(self, tag, attrs):
        token = dict(attrs)
        if tag == "page":
            self.data["type"] = tag
            if "width" in token and "height" in token:
                width = scale(float(token["width"]), self.resolution[0])
                height = scale(float(token["height"]), self.resolution[1])

                # if we have a double-width page, assume the image is on the
                # left and the text on the right.
                if width == 2 * self.image_size[0] and height == self.image_size[1]:
                    self.offset = self.image_size[0]

                self.data["bbox"] = [0, 0, width - self.offset, height]

                self.boxes.append(self.data)

        elif tag == "word":
            self.data = {}
            self.data["type"] = tag
            self.data["bbox"] = [
                scale(float(token["xmin"]), self.resolution[0]) - self.offset,
                scale(float(token["ymin"]), self.resolution[1]),
                scale(float(token["xmax"]), self.resolution[0]) - self.offset,
                scale(float(token["ymax"]), self.resolution[1]),
            ]

        # if we have previous data, add the new data to the
        # contents of the previous data point
        if self.stack and self.data != self.stack[-1] and "bbox" in self.data:
            if "contents" not in self.stack[-1]:
                self.stack[-1]["contents"] = []
            self.stack[-1]["contents"].append(self.data)

        # put the new data point on the stack
        if "bbox" in self.data:
            self.stack.append(self.data)

    def handle_endtag(self, tag):
        if self.stack:
            self.data = self.stack.pop()

    def handle_data(self, data):
        data = data.rstrip()
        if data != "":
            self.data["text"] = data


def _pdftotext2boxes(html, resolution, image_size):
    xresolution, yresolution = resolution
    imagew, imageh = image_size
    parser = PDFTextParser(xresolution, yresolution, imagew, imageh)
    parser.feed(html)
    return parser.boxes


def scale(value, resolution):
    "convert the given value from mm to pixels"
    return int(value * resolution // POINTS_PER_INCH + HALF)


def _bbox_to_hocr(bbox, prev_depth, tags):

    string = ""
    if prev_depth is not None:
        if prev_depth >= bbox["depth"]:
            string += "</" + tags.pop() + ">\n"
            prev_depth -= 1
        else:
            string += "\n"

    x_1, y_1, x_2, y_2 = bbox["bbox"]
    bbox_type = "ocr_" + bbox["type"]
    tag = "span"
    if bbox["type"] == "page":
        tag = "div"

    elif re.search(r"^(?:carea|column)$", bbox["type"]):
        bbox_type = "ocr_carea"
        tag = "div"

    elif bbox["type"] == "para":
        bbox_type = "ocr_par"
        tag = "p"

    string += " " * (2 + bbox["depth"]) + f"<{tag} class='{bbox_type}'"
    string += f" id='{bbox['id']}'"
    string += f" title='bbox {x_1} {y_1} {x_2} {y_2}"
    if "baseline" in bbox:
        string += "; baseline " + " ".join([str(x) for x in bbox["baseline"]])

    if "textangle" in bbox:
        string += f"; textangle {bbox['textangle']}"

    if "confidence" in bbox:
        string += f"; x_wconf {bbox['confidence']}"

    string += "'>"
    string += _text2hocr(bbox)
    tags.append(tag)
    return string, bbox["depth"]


def _text2hocr(bbox):
    string = ""
    if "text" in bbox:
        if "style" in bbox:
            for style in bbox["style"]:
                string += f"<{style}>"

        string += bbox["text"]

        if "style" in bbox:
            for style in reversed(bbox["style"]):
                string += f"</{style}>"
    return string


def _crop_axis(text1, text2, crop1, crop2):

    if text1 > crop2 or text2 < crop1:
        return None, None

    # crop inside edges of box
    if text1 <= crop1 and text2 >= crop2:
        text1 = 0
        text2 = crop2 - crop1

    # crop outside edges of box
    elif text1 >= crop1 and text2 <= crop2:
        text1 -= crop1
        text2 -= crop1

    # crop over 2nd edge of box
    elif crop1 <= text2 <= crop2:
        text1 = 0
        text2 -= crop1

    # crop over 1st edge of box
    # elif crop1 <= text1 <= crop2:
    else:
        text1 -= crop1
        text2 = crop2 - crop1

    return text1, text2
