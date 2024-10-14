"Test brightness contrast"

import subprocess
import tempfile
from page import VERSION
from gi.repository import GLib
from document import Document


def test_1(import_in_mainloop, clean_up_files):
    "Test brightness contrast"

    subprocess.run(["convert", "rose:", "test.gif"], check=True)

    slist = Document()

    dirname = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    slist.set_dir(dirname.name)

    import_in_mainloop(slist, ["test.gif"])

    assert slist.data[0][2].width == 70, "width before crop"
    assert slist.data[0][2].height == 46, "height before crop"

    slist.data[0][2].saved = True
    hocr = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf 2.7.0' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 70 46'>
   <span class='ocr_word' title='bbox 0 0 9 46'>left</span>
   <span class='ocr_word' title='bbox 10 0 45 46'>middle</span>
   <span class='ocr_word' title='bbox 46 0 70 46'>right</span>
  </div>
 </body>
</html>
"""
    slist.data[0][2].import_hocr(hocr)

    mlp = GLib.MainLoop()
    slist.split_page(
        direction="v",
        position=35,
        page=slist.data[0][2].uuid,
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert slist.data[0][2].width == 35, "1st page width after split"
    assert slist.data[0][2].height == 46, "1st page height after split"
    image = slist.data[0][2].image_object
    assert image.width == 35, "1st image width after crop"
    assert image.height == 46, "1st image height after crop"
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 35 46'>
   <span class='ocr_word' title='bbox 0 0 9 46'>left</span>
   <span class='ocr_word' title='bbox 10 0 35 46'>middle</span>
  </div>
 </body>
</html>
"""
    assert slist.data[0][2].export_hocr() == hocr, "split hocr"

    assert slist.data[1][2].width == 35, "2nd page width after split"
    assert slist.data[1][2].height == 46, "2nd page height after split"
    image = slist.data[1][2].image_object
    assert image.width == 35, "2nd image width after crop"
    assert image.height == 46, "2nd image height after crop"
    hocr = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='gscan2pdf {VERSION}' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocr_word'/>
 </head>
 <body>
  <div class='ocr_page' title='bbox 0 0 35 46'>
   <span class='ocr_word' title='bbox 0 0 10 46'>middle</span>
   <span class='ocr_word' title='bbox 11 0 35 46'>right</span>
  </div>
 </body>
</html>
"""
    assert slist.data[1][2].export_hocr() == hocr, "split hocr"

    assert not slist.scans_saved(), "modification removed saved tag"

    #########################

    clean_up_files(["test.gif"])
