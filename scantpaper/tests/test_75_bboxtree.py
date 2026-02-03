"Tests for bboxtree"

from bboxtree import Bboxtree, VERSION, HOCR_HEADER
import pytest


def test_1():
    "tests for bboxtree"

    tree = Bboxtree()
    tree.from_hocr(None)
    assert tree.bbox_tree == [], "no hocr"

    #########################

    expected = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
 </body>
</html>
"""
    assert tree.to_hocr() == expected, "to_hocr empty tree"

    #########################

    hocr = """<!DOCTYPE html PUBLIC "-//W3C//DTD
HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name='ocr-system' content='tesseract'>
</head>
<body>
<div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 422 61'>
<div class='ocr_carea' id='block_1_1' title="bbox 1 14 420 59">
<p class='ocr_par'>
<span class='ocr_line' id='line_1_1' title="bbox 1 14 420 59; baseline -0.003 -17">
 <span class='ocrx_word' id='word_1_1' title="bbox 1 14 77 48">
  <span class='xocr_word' id='xword_1_1' title="x_wconf -3 textangle 90">The</span></span>
 <span class='ocrx_word' id='word_1_2' title="bbox 92 14 202 59">
  <span class='xocr_word' id='xword_1_2' title="x_wconf -3">quick</span></span>
 <span class='ocrx_word' id='word_1_3' title="bbox 214 14 341 48">
  <span class='xocr_word' id='xword_1_3' title="x_wconf -3">brown</span></span>
 <span class='ocrx_word' id='word_1_4' title="bbox 355 14 420 48">
  <span class='xocr_word' id='xword_1_4' title="x_wconf -4">fox</span></span>
</span>
</p>
</div>
</div>
</body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    bbox_iter = tree.each_bbox()
    assert next(bbox_iter) == {
        "type": "page",
        "id": "page_1",
        "bbox": [0, 0, 422, 61],
        "depth": 0,
    }, "page from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "column",
        "id": "block_1_1",
        "bbox": [1, 14, 420, 59],
        "depth": 1,
    }, "column from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "line",
        "id": "line_1_1",
        "bbox": [1, 14, 420, 59],
        "depth": 2,
        "baseline": [-0.003, -17],
    }, "line from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "word",
        "id": "word_1_1",
        "bbox": [1, 14, 77, 48],
        "text": "The",
        "textangle": 90,
        "confidence": -3,
        "depth": 3,
    }, "The from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "word",
        "id": "word_1_2",
        "bbox": [92, 14, 202, 59],
        "text": "quick",
        "confidence": -3,
        "depth": 3,
    }, "quick from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "word",
        "id": "word_1_3",
        "bbox": [214, 14, 341, 48],
        "text": "brown",
        "confidence": -3,
        "depth": 3,
    }, "brown from tesseract 3.00"
    assert next(bbox_iter) == {
        "type": "word",
        "id": "word_1_4",
        "bbox": [355, 14, 420, 48],
        "text": "fox",
        "confidence": -4,
        "depth": 3,
    }, "fox from tesseract 3.00"
    with pytest.raises(StopIteration):
        next(bbox_iter)

    #########################

    expected = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59; baseline -0.003 -17'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; textangle 90; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    assert tree.to_hocr() == expected, "to_hocr basic functionality"

    #########################

    tree = Bboxtree()
    tree.from_text("The quick brown fox", 422, 61)
    bbox_iter = tree.each_bbox()
    simple_box = {
        "type": "page",
        "bbox": [0, 0, 422, 61],
        "text": "The quick brown fox",
        "depth": 0,
    }
    assert next(bbox_iter) == simple_box, "page from plain text"

    expected = """(page 0 0 422 61 "The quick brown fox")
"""
    assert tree.to_djvu_txt() == expected, "to_djvu_txt from simple text"

    #########################

    expected = (
        '[{"type": "page", "bbox": [0, 0, 422, 61], '
        + '"text": "The quick brown fox", "depth": 0}]'
    )
    assert tree.json() == expected, "to json"
    assert Bboxtree(expected).bbox_tree == [simple_box], "from json"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.02.01' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 494 57; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 9 490 55">
    <p class='ocr_par' dir='ltr' id='par_1' title="bbox 1 9 490 55">
     <span class='ocr_line' id='line_1' title="bbox 1 9 490 55">
      <span class='ocrx_word' id='word_1' title="bbox 1 9 88 45"><strong>The</strong></span>
      <span class='ocrx_word' id='word_2' title="bbox 106 9 235 55">quick</span>
      <span class='ocrx_word' id='word_3' title="bbox 253 9 397 45"><em><strong>brown</strong></em></span>
      <span class='ocrx_word' id='word_4' title="bbox 416 9 490 45"><strong><em>fox</em></strong></span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    expected = [
        {
            "type": "page",
            "id": "page_1",
            "bbox": [0, 0, 494, 57],
            "depth": 0,
        },
        {
            "type": "column",
            "id": "block_1_1",
            "bbox": [1, 9, 490, 55],
            "depth": 1,
        },
        {
            "type": "para",
            "id": "par_1",
            "bbox": [1, 9, 490, 55],
            "depth": 2,
        },
        {
            "type": "line",
            "id": "line_1",
            "bbox": [1, 9, 490, 55],
            "depth": 3,
        },
        {
            "type": "word",
            "id": "word_1",
            "bbox": [1, 9, 88, 45],
            "text": "The",
            "depth": 4,
            "style": ["strong"],
        },
        {
            "type": "word",
            "id": "word_2",
            "bbox": [106, 9, 235, 55],
            "depth": 4,
            "text": "quick",
        },
        {
            "type": "word",
            "id": "word_3",
            "bbox": [253, 9, 397, 45],
            "text": "brown",
            "depth": 4,
            "style": ["em", "strong"],
        },
        {
            "type": "word",
            "id": "word_4",
            "bbox": [416, 9, 490, 45],
            "text": "fox",
            "depth": 4,
            "style": ["strong", "em"],
        },
    ]
    assert tree.bbox_tree == expected, "Boxes from tesseract 3.02.01"

    #########################

    expected = (
        HOCR_HEADER
        + """
  <div class='ocr_page' id='page_1' title='bbox 0 0 494 57'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 9 490 55'>
    <p class='ocr_par' id='par_1' title='bbox 1 9 490 55'>
     <span class='ocr_line' id='line_1' title='bbox 1 9 490 55'>
      <span class='ocrx_word' id='word_1' title='bbox 1 9 88 45'><strong>The</strong></span>
      <span class='ocrx_word' id='word_2' title='bbox 106 9 235 55'>quick</span>
      <span class='ocrx_word' id='word_3' title='bbox 253 9 397 45'><em><strong>brown</strong></em></span>
      <span class='ocrx_word' id='word_4' title='bbox 416 9 490 45'><strong><em>fox</em></strong></span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    )
    assert tree.to_hocr() == expected, "to_hocr with par and style"


def test_2():
    "tests for bboxtree"

    hocr = """<!DOCTYPE html PUBLIC "-//W3C//DTD
HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><head><title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name='ocr-system' content='openocr'>
</head>
<body><div class='ocr_page' id='page_1' title='image "test.bmp"; bbox 0 0 422 61'>
<p><span class='ocr_line' id='line_1' title="bbox 1 15 420 60">The quick brown fox<span class='ocr_cinfo' title="x_bboxes 1 15 30 49 31 15 55 49 57 27 77 49 -1 -1 -1 -1 92 27 114 60 116 27 139 49 141 15 153 49 155 27 175 49 176 15 202 49 -1 -1 -1 -1 214 15 237 49 239 27 256 49 257 27 279 49 282 27 315 49 317 27 341 49 -1 -1 -1 -1 355 15 373 49 372 27 394 49 397 27 420 49 "></span></span>
</p>
<p><span class='ocr_line' id='line_2' title="bbox 0 0 0 0"></span>
</p>
</div></body></html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    expected = [
        {
            "type": "page",
            "id": "page_1",
            "bbox": [0, 0, 422, 61],
            "depth": 0,
        },
        {
            "type": "line",
            "id": "line_1",
            "bbox": [1, 15, 420, 60],
            "text": "The quick brown fox",
            "depth": 1,
        },
    ]
    assert tree.bbox_tree == expected, "Boxes from cuneiform 1.0.0"

    #########################

    expected = """(page 0 0 422 61
  (line 1 1 420 46 "The quick brown fox"))
"""

    assert tree.to_djvu_txt() == expected, "djvu from cuneiform 1.0.0"

    #########################

    tree.bbox_tree[0]["text"] = "to be ignored"
    assert (
        tree.to_djvu_txt() == expected
    ), "djvu does not allow text items to have children"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "0020_1L.tif"; bbox 0 0 2236 3185; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 157 80 1725 174">
    <p class='ocr_par' dir='ltr' id='par_1_1' title="bbox 157 84 1725 171">
     <span class='ocr_line' id='line_1_1' title="bbox 157 84 1725 171; baseline -0.003 -17">
      <span class='ocrx_word' id='word_1_1' title='bbox 157 90 241 155; x_wconf 85' lang='fra'>28</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 533 86 645 152; x_wconf 90' lang='fra' dir='ltr'>LA</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 695 86 1188 171; x_wconf 75' lang='fra' dir='ltr'>MARQUISE</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 1229 87 1365 151; x_wconf 90' lang='fra' dir='ltr'>DE</span>
      <span class='ocrx_word' id='word_1_5' title='bbox 1409 84 1725 154; x_wconf 82' lang='fra' dir='ltr'><em>GANGE</em></span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    expected = """(page 0 0 2236 3185
  (column 157 3011 1725 3105
    (para 157 3014 1725 3101
      (line 157 3014 1725 3101
        (word 157 3030 241 3095 "28")
        (word 533 3033 645 3099 "LA")
        (word 695 3014 1188 3099 "MARQUISE")
        (word 1229 3034 1365 3098 "DE")
        (word 1409 3031 1725 3101 "GANGE")))))
"""

    assert tree.to_djvu_txt() == expected, "djvu_txt with hiearchy"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "0020_1L.tif"; bbox 0 0 2236 3185; ppageno 0'>
   <div class='ocr_carea' id='block_1_5' title="bbox 1808 552 2290 1020">
    <p class='ocr_par' dir='ltr' id='par_1_6' title="bbox 1810 552 2288 1020">
     <span class='ocr_line' id='line_1_9' title="bbox 1810 552 2288 1020; baseline 2487">
      <span class='ocrx_word' id='word_1_17' title='bbox 1810 552 2288 1020; x_wconf 95' lang='deu' dir='ltr'></span> 
     </span>
    </p>
   </div>
  </div>
  <div class='page' id='page_2' title='image "0020_1L.tif"; bbox 0 0 2236 3185; ppageno 0'>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    assert tree.to_djvu_txt() == "", "ignore hierachy with no contents"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "/tmp/gscan2pdf-Ay0J/nUVvJ79mSJ.pnm"; bbox 0 0 2480 3507; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 295 263 546 440">
    <p class='ocr_par' dir='ltr' id='par_1_1' title="bbox 297 263 545 440">
     <span class='ocr_line' id='line_1_1' title="bbox 368 263 527 310; baseline 0 3197">
      <span class='ocrx_word' id='word_1_1' title='bbox 368 263 527 310; x_wconf 95' lang='deu' dir='ltr'> </span> 
     </span>
     <span class='ocr_line' id='line_1_2' title="bbox 297 310 545 440; baseline 0 0">
      <span class='ocrx_word' id='word_1_2' title='bbox 297 310 545 440; x_wconf 95' lang='deu' dir='ltr'>  </span> 
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    assert tree.to_djvu_txt() == "", "ignore hierachy with no contents 2"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title>
</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.03' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "/tmp/gscan2pdf-jzAZ/YHm7vp6nUp.pnm"; bbox 0 0 2480 3507; ppageno 0'>
   <div class='ocr_carea' id='block_1_10' title="bbox 305 2194 2082 2573">
    <p class='ocr_par' dir='ltr' id='par_1_13' title="bbox 306 2195 2079 2568">
     <span class='ocr_line' id='line_1_43' title="bbox 311 2382 1920 2428; baseline -0.009 -3">
      <span class='ocrx_word' id='word_1_401' title='bbox 1198 2386 1363 2418; x_wconf 77' lang='deu' dir='ltr'><strong>Kauﬂ&lt;raft</strong></span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    expected = """(page 0 0 2480 3507
  (column 305 934 2082 1313
    (para 306 939 2079 1312
      (line 311 1079 1920 1125
        (word 1198 1089 1363 1121 "Kauﬂ<raft")))))
"""
    assert tree.to_djvu_txt() == expected, "deal with encoded characters"

    #########################

    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
  <meta name='ocr-system' content='tesseract 4.1.1' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "bug.tif"; bbox 0 0 2480 3507; ppageno 0'>
   <div class='ocr_carea' id='block_1_3' title="bbox 253 443 782 528">
    <p class='ocr_par' id='par_1_3' lang='deu' title="bbox 253 443 782 528">
     <span class='ocr_header' id='line_1_3' title="bbox 255 443 782 480; baseline -0.009 0; x_size 38.437073; x_descenders 5.4370708; x_ascenders 9">
      <span class='ocrx_word' id='word_1_6' title='bbox 255 447 335 480; x_wconf 93'>GLS</span>
     </span>
     <span class='ocr_header' id='_1_3' title="bbox 255 443 782 480; baseline -0.009 0; x_size 38.437073; x_descenders 5.4370708; x_ascenders 9">
      <span class='ocrx_word' id='word_1_6' title='bbox 255 447 335 480; x_wconf 93'>GLS</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    expected = """(page 0 0 2480 3507
  (column 253 2979 782 3064
    (para 253 2979 782 3064
      (line 255 3027 782 3064
        (word 255 3027 335 3060 "GLS"))
      (line 255 3027 782 3064
        (word 255 3027 335 3060 "GLS")))))
"""
    assert tree.to_djvu_txt() == expected, "deal with unsupported box types"

    #########################

    # hOCR created with:
    # convert +matte -depth 1 -pointsize 12 -units PixelsPerInch \
    #         -density 300 label:"The\nquick brown fox\n\njumps over the lazy dog." test.png
    # tesseract -l eng -c tessedit_create_hocr=1 test.png stdout

    hocr = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='tesseract 3.05.01' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
</head>
<body>
  <div class='ocr_page' id='page_1' title='image "test.png"; bbox 0 0 545 229; ppageno 0'>
   <div class='ocr_carea' id='block_1_1' title="bbox 1 10 348 113">
    <p class='ocr_par' id='par_1_1' lang='eng' title="bbox 1 10 348 113">
     <span class='ocr_line' id='line_1_1' title="bbox 1 10 85 46; baseline 0 0; x_size 46.247379; x_descenders 10.247379; x_ascenders 10">
      <span class='ocrx_word' id='word_1_1' title='bbox 1 10 85 46; x_wconf 90'>The</span>
     </span>
     <span class='ocr_line' id='line_1_2' title="bbox 2 67 348 113; baseline 0 -10; x_size 46; x_descenders 10; x_ascenders 10">
      <span class='ocrx_word' id='word_1_2' title='bbox 2 67 116 113; x_wconf 89'>quick</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 134 67 264 103; x_wconf 94'>brown</span>
      <span class='ocrx_word' id='word_1_4' title='bbox 282 67 348 103; x_wconf 94'>fox</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_2' title="bbox 0 181 541 227">
    <p class='ocr_par' id='par_1_2' lang='eng' title="bbox 0 181 541 227">
     <span class='ocr_line' id='line_1_3' title="bbox 0 181 541 227; baseline 0 -10; x_size 46; x_descenders 10; x_ascenders 10">
      <span class='ocrx_word' id='word_1_5' title='bbox 0 181 132 227; x_wconf 90'>jumps</span>
      <span class='ocrx_word' id='word_1_6' title='bbox 150 191 246 217; x_wconf 90'>over</span>
      <span class='ocrx_word' id='word_1_7' title='bbox 261 181 328 217; x_wconf 90'>the</span>
      <span class='ocrx_word' id='word_1_8' title='bbox 347 181 432 227; x_wconf 90'>lazy</span>
      <span class='ocrx_word' id='word_1_9' title='bbox 449 181 541 227; x_wconf 93'>dog.</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    tree = Bboxtree()
    tree.from_hocr(hocr)
    assert (
        tree.to_text() == "The quick brown fox\n\njumps over the lazy dog."
    ), "string with paragraphs"


def test_from_djvu_txt():
    "tests for bboxtree.from_djvu_txt()"
    djvu = """(page 0 0 2236 3185
  (column 157 3011 1725 3105
    (para 157 3014 1725 3101
      (line 157 3014 1725 3101
        (word 157 3030 241 3095 "28")
        (word 533 3033 645 3099 "LA")
        (word 695 3014 1188 3099 "MARQUISE")
        (word 1229 3034 1365 3098 "DE")
        (word 1409 3031 1725 3101 "GANGE")))))
"""

    expected = [
        {
            "type": "page",
            "bbox": [
                0,
                0,
                2236,
                3185,
            ],
            "depth": 0,
        },
        {
            "type": "column",
            "bbox": [
                157,
                80,
                1725,
                174,
            ],
            "depth": 1,
        },
        {
            "type": "para",
            "bbox": [
                157,
                84,
                1725,
                171,
            ],
            "depth": 2,
        },
        {
            "type": "line",
            "bbox": [
                157,
                84,
                1725,
                171,
            ],
            "depth": 3,
        },
        {
            "type": "word",
            "bbox": [
                157,
                90,
                241,
                155,
            ],
            "depth": 4,
            "text": "28",
        },
        {
            "type": "word",
            "bbox": [
                533,
                86,
                645,
                152,
            ],
            "depth": 4,
            "text": "LA",
        },
        {
            "type": "word",
            "bbox": [
                695,
                86,
                1188,
                171,
            ],
            "depth": 4,
            "text": "MARQUISE",
        },
        {
            "type": "word",
            "bbox": [
                1229,
                87,
                1365,
                151,
            ],
            "depth": 4,
            "text": "DE",
        },
        {
            "type": "word",
            "bbox": [
                1409,
                84,
                1725,
                154,
            ],
            "depth": 4,
            "text": "GANGE",
        },
    ]
    tree = Bboxtree()
    tree.from_djvu_txt(djvu)
    assert tree.bbox_tree == expected, "from_djvu_txt() basic functionality"

    #########################

    djvu = """(page 0 0 2480 3507
  (word 157 3030 241 3095 "()"))
"""
    expected = [
        {
            "type": "page",
            "bbox": [
                0,
                0,
                2480,
                3507,
            ],
            "depth": 0,
        },
        {
            "type": "word",
            "bbox": [
                157,
                412,
                241,
                477,
            ],
            "depth": 1,
            "text": "()",
        },
    ]
    tree = Bboxtree()
    tree.from_djvu_txt(djvu)
    assert tree.bbox_tree == expected, "from_djvu_txt() with quoted brackets"

    djvu = """(page 0 0 2480 3507
  (word 157 3030 241 "()"))
"""
    with pytest.raises(ValueError):
        tree.from_djvu_txt(djvu)

    #########################

    ann = """(maparea "" "()" (rect 157 3030 84 65) (hilite #cccf00) (xor))
"""
    assert tree.to_djvu_ann() == ann, "to_djvu_ann() basic functionality"

    tree = Bboxtree()
    tree.from_djvu_ann(ann, 2480, 3507)
    assert tree.bbox_tree == expected, "from_djvu_ann() basic functionality"

    with pytest.raises(ValueError):
        tree.from_djvu_ann(
            """(maparea "" "()" (rect 157 3030 84 65) (hilite #cccg00) (xor))
""",
            2480,
            3507,
        )


def test_from_pdftotext():
    "tests for bboxtree.from_pdftotext()"

    pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>untitled</title>
<meta name="Producer" content="Tesseract 3.03"/>
<meta name="CreationDate" content=""/>
</head>
<body>
<doc>
  <page width="464.910000" height="58.630000">
    <word xMin="1.029000" yMin="22.787000" xMax="87.429570" yMax="46.334000">The</word>
    <word xMin="105.029000" yMin="22.787000" xMax="222.286950" yMax="46.334000">quick</word>
    <word xMin="241.029000" yMin="22.787000" xMax="374.744000" yMax="46.334000">brown</word>
    <word xMin="393.029000" yMin="22.787000" xMax="460.914860" yMax="46.334000">fox</word>
  </page>
</doc>
</body>
</html>
"""
    expected = [
        {
            "type": "page",
            "bbox": [
                0,
                0,
                464,
                58,
            ],
            "depth": 0,
        },
        {
            "type": "word",
            "bbox": [
                1,
                22,
                87,
                46,
            ],
            "depth": 1,
            "text": "The",
        },
        {
            "type": "word",
            "bbox": [
                105,
                22,
                222,
                46,
            ],
            "depth": 1,
            "text": "quick",
        },
        {
            "type": "word",
            "bbox": [
                241,
                22,
                374,
                46,
            ],
            "depth": 1,
            "text": "brown",
        },
        {
            "type": "word",
            "bbox": [
                393,
                22,
                460,
                46,
            ],
            "depth": 1,
            "text": "fox",
        },
    ]
    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (72, 72), (59, 465))
    assert tree.bbox_tree == expected, "from_pdftotext() basic functionality"

    #########################

    expected = [
        {
            "type": "page",
            "bbox": [
                0,
                0,
                1937,
                244,
            ],
            "depth": 0,
        },
        {
            "type": "word",
            "bbox": [
                4,
                94,
                364,
                193,
            ],
            "depth": 1,
            "text": "The",
        },
        {
            "type": "word",
            "bbox": [
                437,
                94,
                926,
                193,
            ],
            "depth": 1,
            "text": "quick",
        },
        {
            "type": "word",
            "bbox": [
                1004,
                94,
                1561,
                193,
            ],
            "depth": 1,
            "text": "brown",
        },
        {
            "type": "word",
            "bbox": [
                1637,
                94,
                1920,
                193,
            ],
            "depth": 1,
            "text": "fox",
        },
    ]
    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (300, 300), (244, 1937))
    assert tree.bbox_tree == expected, "from_pdftotext() with resolution"

    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (300, 300), (968.5, 244))
    expected[0]["bbox"] = [0, 0, 968.5, 244]
    expected[1]["bbox"] = [-964.5, 94, -604.5, 193]
    expected[2]["bbox"] = [-531.5, 94, -42.5, 193]
    expected[3]["bbox"] = [35.5, 94, 592.5, 193]
    expected[4]["bbox"] = [668.5, 94, 951.5, 193]
    assert tree.bbox_tree == expected, "from_pdftotext() double width"

    pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title></title>
<meta name="Producer" content="Tesseract 3.03"/>
<meta name="CreationDate" content=""/>
</head>
</html>
"""
    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (72, 72), (59, 465))
    assert tree.bbox_tree == [], "from_pdftotext() no body"

    pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title></title>
<meta name="Producer" content="Tesseract 3.03"/>
<meta name="CreationDate" content=""/>
</head>
<body>
</body>
</html>
"""
    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (72, 72), (59, 465))
    assert tree.bbox_tree == [], "from_pdftotext() no boxes"

    pdftext = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title></title>
<meta name="Producer" content="Tesseract 3.03"/>
<meta name="CreationDate" content=""/>
</head>
<body>
<doc>
  <page width="464.910000">
    <word xMin="1.029000" yMin="22.787000" xMax="87.429570" yMax="46.334000">The</word>
  </page>
</doc>
</body>
</html>
"""
    expected = []
    tree = Bboxtree()
    tree.from_pdftotext(pdftext, (72, 72), (59, 465))
    assert tree.bbox_tree == expected, "from_pdftotext() invalid page"


def test_valid():
    "test valid() method"
    tree = Bboxtree()
    tree.from_text("The quick brown fox", 422, 61)
    assert tree.valid(), "valid"

    tree.bbox_tree[0]["bbox"][3] = 0
    assert not tree.valid(), "invalid bbox value"

    tree.bbox_tree[0]["type"] = "word"
    assert tree.valid(), "valid"

    tree.bbox_tree = []
    assert not tree.valid(), "empty tree"


def test_crop():
    "test crop() method"
    tree = Bboxtree()
    tree.from_text("The quick brown fox", 422, 61)
    tree.crop(10, 10, 390, 30)
    assert tree.bbox_tree == [
        {
            "bbox": [0, 0, 390, 30],
            "depth": 0,
            "text": "The quick brown fox",
            "type": "page",
        },
    ], "crop inside"

    tree.crop(200, -1, 200, 30)
    assert tree.bbox_tree == [
        {
            "bbox": [0, 1, 190, 30],
            "depth": 0,
            "text": "The quick brown fox",
            "type": "page",
        },
    ], "crop top right"

    tree.crop(0, 40, 200, 30)
    assert tree.bbox_tree == [], "crop outside"
