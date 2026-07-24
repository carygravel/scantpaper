"Test Document tools"

import re
import subprocess
from unittest.mock import MagicMock
from PIL import Image
import pytest
from document import Document
import config
from const import VERSION
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib  # pylint: disable=wrong-import-position
from loop_helpers import safe_mainloop


def test_rotate(
    rose_jpg, temp_db, import_in_mainloop, set_saved_in_mainloop, get_page_sync
):
    "Test rotating"
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    set_saved_in_mainloop(slist, 1, True)
    assert slist.data[0][1].get_height() == 65, "thumbnail height before rotation"
    assert slist.data[0][1].get_width() == 100, "thumbnail width before rotation"

    asserts = 0

    def display_cb(response):
        nonlocal asserts
        assert True, "Triggered display callback"
        asserts += 1

    mlp = safe_mainloop(2000)
    slist.rotate(
        angle=-90,
        page=slist.data[0][2],
        display_callback=display_cb,
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    assert asserts == 1, "all callbacks run"
    page = get_page_sync(slist.thread, number=1)
    assert page.image_object.mode == "RGB", "valid JPG created"
    assert not slist.thread.pages_saved(), "modification removed saved tag"
    assert slist.data[0][1].get_height() == 100, "thumbnail height after rotation"
    assert slist.data[0][1].get_width() == 65, "thumbnail width after rotation"


def test_analyse_blank(import_in_mainloop, temp_db, clean_up_files, get_page_sync):
    "Test analyse"

    subprocess.run(
        [config.CONVERT_COMMAND, "-size", "10x10", "xc:white", "white.pgm"], check=True
    )

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["white.pgm"])

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert page.std_dev == [0.0], "Found blank page"

    #########################

    clean_up_files(["white.pgm"])


def test_analyse_dark(import_in_mainloop, temp_db, clean_up_files, get_page_sync):
    "Test analyse"

    subprocess.run([config.CONVERT_COMMAND, "xc:black", "black.pgm"], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, ["black.pgm"])

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert page.mean == [0.0], "Found dark page"

    #########################

    clean_up_files(["black.pgm"])


def test_threshold(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    rose_jpg,
    get_page_sync,
):
    "Test threshold"
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    set_saved_in_mainloop(slist, 1, True)
    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]',
    )

    mlp = safe_mainloop(2000)
    slist.threshold(
        threshold=80,
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert len(page.mean) == 1, "depth == 1"
    assert re.search("ACCOUNT", page.text_layer), "OCR output still there"
    assert not slist.thread.pages_saved(), "modification removed saved tag"


image_types = [
    ["pnm", "L", 255, 255],
    ["png", "RGBA", (255, 255, 255, 255), 255],
]
xfail_image_types = [
    pytest.param("png", "P", 255, 1.0, marks=pytest.mark.xfail),
]


@pytest.mark.parametrize(
    "suffix, mode, white, expected_mean", image_types + xfail_image_types
)
def test_negate(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    clean_up_files,
    suffix,
    mode,
    white,
    expected_mean,
    get_page_sync,
):
    "Test negate"

    image = f"white.{suffix}"
    im = Image.new(mode, [1, 1], color=white)
    im.save(image)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [image])
    set_saved_in_mainloop(slist, 1, True)
    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]',
    )

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    page = get_page_sync(slist.thread, number=1)
    assert min(page.mean) == expected_mean, "mean before"

    mlp = safe_mainloop(2000)
    slist.negate(
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert max(page.mean) == 0, "mean afterwards"
    assert re.search("ACCOUNT", page.text_layer), "OCR output still there"
    assert not slist.thread.pages_saved(), "modification removed saved tag"

    #########################

    clean_up_files([image])


def test_unsharp_mask(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    rose_jpg,
    get_page_sync,
):
    "Test unsharp mask"
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    set_saved_in_mainloop(slist, 1, True)
    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]',
    )

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    page = get_page_sync(slist.thread, number=1)
    assert page.mean == [
        179.97422360248447,
        65.09254658385093,
        99.69409937888199,
    ], "mean before"

    mlp = safe_mainloop(2000)
    slist.unsharp(
        radius=1,
        percent=200,
        threshold=3,
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, number=1)
    assert page.mean != [
        179.97422360248447,
        65.09254658385093,
        99.69409937888199,
    ], "mean after"
    assert re.search("ACCOUNT", page.text_layer), "OCR output still there"
    assert not slist.thread.pages_saved(), "modification removed saved tag"


def test_crop(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    temp_gif,
    get_page_sync,
):
    "Test brightness contrast"

    subprocess.run([config.CONVERT_COMMAND, "rose:", temp_gif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_gif.name])

    page = get_page_sync(slist.thread, number=1)
    assert page.width == 70, "width before crop"
    assert page.height == 46, "height before crop"

    set_saved_in_mainloop(slist, 1, True)
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 70 46'>
      <span class='ocrx_word' title='bbox 1 1 9 9'>beyond br</span>
      <span class='ocrx_word' title='bbox 5 5 15 15'>on br</span>
      <span class='ocrx_word' title='bbox 11 11 19 19'>inside</span>
      <span class='ocrx_word' title='bbox 15 15 25 25'>on tl</span>
      <span class='ocrx_word' title='bbox 21 21 29 29'>beyond tl</span>
  </div>
 </body>
</html>
"""
    page = get_page_sync(slist.thread, number=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    mlp = safe_mainloop(2000)
    slist.crop(
        x=10,
        y=10,
        w=10,
        h=10,
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    page = get_page_sync(slist.thread, number=1)
    assert page.width == 10, "page width after crop"
    assert page.height == 10, "page height after crop"
    image = page.image_object
    assert image.width == 10, "image width after crop"
    assert image.height == 10, "image height after crop"
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 10 10'>
   <span class='ocrx_word' title='bbox 0 0 5 5'>on br</span>
   <span class='ocrx_word' title='bbox 1 1 9 9'>inside</span>
   <span class='ocrx_word' title='bbox 5 5 10 10'>on tl</span>
  </div>
 </body>
</html>
"""
    assert page.export_hocr() == hocr, "cropped hocr"
    assert not slist.thread.pages_saved(), "modification removed saved tag"


def test_split(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    temp_gif,
    get_page_sync,
):
    "Test split"

    subprocess.run([config.CONVERT_COMMAND, "rose:", temp_gif.name], check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_gif.name])

    page = get_page_sync(slist.thread, number=1)
    assert page.width == 70, "width before crop"
    assert page.height == 46, "height before crop"

    set_saved_in_mainloop(slist, 1, True)
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 70 46'>
   <span class='ocrx_word' title='bbox 0 0 9 46'>left</span>
   <span class='ocrx_word' title='bbox 10 0 45 46'>middle</span>
   <span class='ocrx_word' title='bbox 46 0 70 46'>right</span>
  </div>
 </body>
</html>
"""
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    mlp = safe_mainloop(2000)
    slist.split_page(
        direction="v",
        position=35,
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    page = get_page_sync(slist.thread, number=1)
    assert page.width == 35, "1st page width after split"
    assert page.height == 46, "1st page height after split"
    assert page.id == 3, "1st page id after split"
    image = page.image_object
    assert image.width == 35, "1st image width after split"
    assert image.height == 46, "1st image height after split"
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 35 46'>
   <span class='ocrx_word' title='bbox 0 0 9 46'>left</span>
   <span class='ocrx_word' title='bbox 10 0 35 46'>middle</span>
  </div>
 </body>
</html>
"""
    assert page.export_hocr() == hocr, "split hocr"

    page = get_page_sync(slist.thread, number=2)
    assert page.width == 35, "2nd page width after split"
    assert page.height == 46, "2nd page height after split"
    assert page.id == 2, "2nd page id after split"
    image = page.image_object
    assert image.width == 35, "2nd image width after split"
    assert image.height == 46, "2nd image height after split"
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='scantpaper {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 35 46'>
   <span class='ocrx_word' title='bbox 0 0 10 46'>middle</span>
   <span class='ocrx_word' title='bbox 11 0 35 46'>right</span>
  </div>
 </body>
</html>
"""
    assert page.export_hocr() == hocr, "split hocr"

    assert not slist.thread.pages_saved(), "modification removed saved tag"


def test_brightness_contrast(
    import_in_mainloop,
    set_saved_in_mainloop,
    set_text_in_mainloop,
    temp_db,
    rose_jpg,
    get_page_sync,
):
    "Test brightness contrast"
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_jpg])
    set_saved_in_mainloop(slist, 1, True)
    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox":["0","0","783","1057"],"id":"page_1",'
        '"type":"page","depth":0},{"depth":1,"id":"word_1_2","type":"word",'
        '"confidence":"93","text":"ACCOUNT","bbox":["218","84","401","109"]}]',
    )
    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    mean = [179.97422360248447, 65.09254658385093, 99.69409937888199]
    page = get_page_sync(slist.thread, number=1)
    assert page.mean == mean, "mean before"

    mlp = safe_mainloop(2000)
    slist.brightness_contrast(
        brightness=65,
        contrast=65,
        page=slist.data[0][2],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    mlp = safe_mainloop(2000)
    slist.analyse(
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    mlp.run()
    page = get_page_sync(slist.thread, number=1)
    assert page.mean != mean, "mean after"
    assert re.search("ACCOUNT", page.text_layer), "OCR output still there"
    assert not slist.thread.pages_saved(), "modification removed saved tag"


def test_race_condition_rotate_save(rose_pnm, temp_db, temp_pdf, import_in_mainloop):
    "Test that saving a page while it's being rotated doesn't cause an error"
    slist = Document(db=temp_db.name)

    # Import a page
    import_in_mainloop(slist, [rose_pnm])
    page_id = slist.data[0][2]

    # Queue a rotate operation. This will eventually call replace_page and increment action_id.
    slist.rotate(page=page_id, angle=90)

    # IMMEDIATELY queue a save operation with the same page_id.
    # It will be behind the rotate operation in the DocThread's queue.
    mlp = safe_mainloop(10000)
    error_callback = MagicMock()

    slist.save_pdf(
        path=temp_pdf.name,
        list_of_pages=[page_id],
        error_callback=error_callback,
        finished_callback=lambda x: mlp.quit(),
    )

    # Wait for both to finish
    mlp.run()

    error_callback.assert_not_called()


def test_race_condition_rotate_rotate(rose_pnm, temp_db, import_in_mainloop):
    "Test rotating the same page twice in a row before the first rotate finishes"
    slist = Document(db=temp_db.name)

    # Import a page
    import_in_mainloop(slist, [rose_pnm])
    page_id = slist.data[0][2]

    # Queue two rotate operations on the same page_id.
    # The first one will replace page_id with a new one.
    # The second one will fail if it uses the old page_id.
    slist.rotate(page=page_id, angle=90)

    mlp = safe_mainloop(10000)
    error_callback = MagicMock()

    slist.rotate(
        page=page_id,
        angle=90,
        error_callback=error_callback,
        finished_callback=lambda x: mlp.quit(),
    )

    # Wait for both to finish
    mlp.run()
    error_callback.assert_not_called()
