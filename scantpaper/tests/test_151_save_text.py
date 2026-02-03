"Test saving text"

import subprocess
import tempfile
from gi.repository import GLib
from document import Document
from bboxtree import VERSION


def test_save_text(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test saving text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": "The quick brown fox", "depth": 3}]',
    )

    with tempfile.NamedTemporaryFile(suffix=".txt") as temp_txt2:
        mlp = GLib.MainLoop()
        slist.save_text(
            path=temp_txt.name,
            list_of_pages=[slist.data[0][2]],
            options={
                "post_save_hook": f"cp %i {temp_txt2.name}",
                "post_save_hook_options": "fg",
            },
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert (
            subprocess.check_output(["cat", temp_txt.name], text=True)
            == "The quick brown fox"
        ), "saved ASCII"
        assert (
            subprocess.check_output(["cat", temp_txt2.name], text=True)
            == "The quick brown fox"
        ), "ran post-save hook"

    clean_up_files(slist.thread.db_files)


def test_save_no_text(rose_pnm, temp_txt, temp_db, import_in_mainloop, clean_up_files):
    "Test saving text"
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_pnm.name])

    with tempfile.NamedTemporaryFile(suffix=".txt") as temp_txt2:
        mlp = GLib.MainLoop()
        slist.save_text(
            path=temp_txt.name,
            list_of_pages=[slist.data[0][2]],
            options={
                "post_save_hook": f"cp %i {temp_txt2.name}",
                "post_save_hook_options": "fg",
            },
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert (
            subprocess.check_output(["cat", temp_txt.name], text=True) == ""
        ), "saved ASCII"
        assert (
            subprocess.check_output(["cat", temp_txt2.name], text=True) == ""
        ), "ran post-save hook"

    clean_up_files(slist.thread.db_files)


def test_save_utf8(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test writing text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    set_text_in_mainloop(
        slist,
        1,
        '[{"bbox": [0, 0, 422, 61], "type": "page", "depth": 0}, '
        '{"bbox": [1, 14, 420, 59], "type": "column", "depth": 1}, '
        '{"bbox": [1, 14, 420, 59], "type": "line", "depth": 2}, '
        '{"bbox": [1, 14, 77, 48], "type": "word", "text": '
        '"пени способствовала сохранению", "depth": 3}]',
    )

    mlp = GLib.MainLoop()
    slist.save_text(
        path=temp_txt.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", temp_txt.name], text=True)
        == "пени способствовала сохранению"
    ), "saved ASCII"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_hocr_as_text(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test saving HOCR as text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    mlp = GLib.MainLoop()
    slist.save_text(
        path=temp_txt.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", temp_txt.name], text=True)
        == "The quick brown fox"
    ), "saved hOCR"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_hocr(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test writing text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    with tempfile.NamedTemporaryFile(suffix=".txt") as temp_txt2:
        mlp = GLib.MainLoop()
        slist.save_hocr(
            path=temp_txt.name,
            list_of_pages=[slist.data[0][2]],
            options={
                "post_save_hook": f"cp %i {temp_txt2.name}",
                "post_save_hook_options": "fg",
            },
            finished_callback=lambda response: mlp.quit(),
        )
        GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
        mlp.run()

        assert (
            subprocess.check_output(["cat", temp_txt.name], text=True) == hocr
        ), "saved hOCR"
        assert (
            subprocess.check_output(["cat", temp_txt2.name], text=True) == hocr
        ), "ran post-save hook"

    clean_up_files(slist.thread.db_files)


def test_save_hocr_with_encoding(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test writing text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 2452 3484'>
   <div class='ocr_carea' id='block_1_9' title='bbox 1249 2403 2165 3246'>
    <p class='ocr_par' id='par_1_12' title='bbox 1250 2403 2165 3245'>
     <span class='ocr_line' id='line_1_70' title='bbox 1251 3205 2162 3245'>
      <span class='ocrx_word' id='word_1_518' title='bbox 1251 3205 1344 3236; x_wconf 92'>donc</span>
      <span class='ocrx_word' id='word_1_519' title='bbox 1359 3213 1401 3237; x_wconf 91'>un</span>
      <span class='ocrx_word' id='word_1_520' title='bbox 1416 3206 1532 3245; x_wconf 86'>village</span>
      <span class='ocrx_word' id='word_1_521' title='bbox 1546 3205 1567 3236; x_wconf 88'>à</span>
      <span class='ocrx_word' id='word_1_522' title='bbox 1581 3205 1700 3237; x_wconf 93'>Cuzco</span>
      <span class='ocrx_word' id='word_1_523' title='bbox 1714 3205 1740 3245; x_wconf 83'>(&lt;&lt;</span>
      <span class='ocrx_word' id='word_1_524' title='bbox 1756 3208 1871 3237; x_wconf 92'>centre</span>
      <span class='ocrx_word' id='word_1_525' title='bbox 1885 3207 1930 3237; x_wconf 93'>du</span>
      <span class='ocrx_word' id='word_1_526' title='bbox 1946 3207 2075 3237; x_wconf 91'>monde</span>
      <span class='ocrx_word' id='word_1_527' title='bbox 2090 3219 2105 3232; x_wconf 88'><strong><em>&gt;&gt;</em></strong></span>
      <span class='ocrx_word' id='word_1_528' title='bbox 2120 3215 2162 3237; x_wconf 93'>en</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    mlp = GLib.MainLoop()
    slist.save_hocr(
        path=temp_txt.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

    assert (
        subprocess.check_output(["cat", temp_txt.name], text=True) == hocr
    ), "saved hOCR"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_multipage_hocr(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test writing text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name, rose_pnm.name])

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)
    set_text_in_mainloop(slist, 2, page.text_layer)

    mlp = GLib.MainLoop()
    slist.save_hocr(
        path=temp_txt.name,
        list_of_pages=[slist.data[0][2], slist.data[1][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 
  <div class='ocr_page' id='page_1' title='bbox 0 0 422 61'>
   <div class='ocr_carea' id='block_1_1' title='bbox 1 14 420 59'>
    <span class='ocr_line' id='line_1_1' title='bbox 1 14 420 59'>
     <span class='ocrx_word' id='word_1_1' title='bbox 1 14 77 48; x_wconf -3'>The</span>
     <span class='ocrx_word' id='word_1_2' title='bbox 92 14 202 59; x_wconf -3'>quick</span>
     <span class='ocrx_word' id='word_1_3' title='bbox 214 14 341 48; x_wconf -3'>brown</span>
     <span class='ocrx_word' id='word_1_4' title='bbox 355 14 420 48; x_wconf -4'>fox</span>
    </span>
   </div>
  </div>
 </body>
</html>
"""
    assert (
        subprocess.check_output(["cat", temp_txt.name], text=True) == hocr
    ), "saved hOCR"

    #########################

    clean_up_files(slist.thread.db_files)


def test_save_hocr_structure(
    import_in_mainloop,
    set_text_in_mainloop,
    rose_pnm,
    temp_db,
    temp_txt,
    clean_up_files,
):
    "Test writing text"
    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [rose_pnm.name])

    hocr = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title></title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name='ocr-system' content='tesseract'>
</head>
<body>
<div class='ocr_page' id='page_1' title='image "test.tif"; bbox 0 0 708 1054'>
<div class='ocr_carea' id='block_1_1' title="bbox 87 578 328 685">
<p class='ocr_par' id='par_1_1' lang='eng' title="bbox 87 578 328 609">
<span class='ocr_line' id='line_1_1' title="bbox 87 578 328 609; baseline 0.01 -7; textangle 0; x_size 31; x_descenders 7; x_ascenders 6">
<span class='ocrx_word' id='word_1_1' title='bbox 87 578 143 602; x_wconf 96'>The1</span>
<span class='ocrx_word' id='word_1_2' title='bbox 154 578 231 609; x_wconf 96'>quick1</span>
<span class='ocrx_word' id='word_1_3' title='bbox 241 578 328 602; x_wconf 96'>brown1</span>
</span>
</p>
</div>
<div class='ocr_carea' id='block_1_2' title="bbox 639 814 708 1054">
<p class='ocr_par' id='par_1_2' lang='eng' title="bbox 639 814 708 1054">
<span class='ocr_line' id='line_1_2' title="bbox 639 814 670 1053; textangle 90; x_size 31; x_descenders 7; x_ascenders 6">
<span class='ocrx_word' id='word_1_4' title='bbox 639 998 663 1053; x_wconf 96'>The2</span>
<span class='ocrx_word' id='word_1_5' title='bbox 639 911 670 987; x_wconf 96'>quick2</span>
<span class='ocrx_word' id='word_1_6' title='bbox 639 814 664 900; x_wconf 96'>brown2</span>
</span>
</p>
</div>
<div class='ocr_carea' id='block_1_3' title='bbox 87 578 328 685'>
<p class='ocr_par' id='par_1_3' title='bbox 87 578 328 685'>
<span class='ocr_header' id='header_1_1' title='bbox 88 578 328 609; baseline 0 -7'>
<span class='ocrx_word' id='word_1_7' title='bbox 88 578 143 602; x_wconf 96'>The</span>
<span class='ocrx_word' id='word_1_8' title='bbox 154 578 230 609; x_wconf 96'>quick</span>
<span class='ocrx_word' id='word_1_9' title='bbox 241 578 328 602; x_wconf 96'>brown</span>
</span>
<span class='ocr_caption' id='caption_1_1' title='bbox 87 616 302 647; baseline 0 -7i; textangle 0;'>
<span class='ocrx_word' id='word_1_10' title='bbox 87 616 130 640; x_wconf 96'>fox</span>
<span class='ocrx_word' id='word_1_11' title='bbox 139 616 228 647; x_wconf 96'>jumps</span>
<span class='ocrx_word' id='word_1_12' title='bbox 239 622 302 640; x_wconf 96'>over</span>
</span>
<span class='ocr_footer' id='footer_1_1' title='bbox 87 654 272 685; baseline -0.005 -7'>
<span class='ocrx_word' id='word_1_13' title='bbox 87 655 132 678; x_wconf 96'>the</span>
<span class='ocrx_word' id='word_1_14' title='bbox 144 654 201 685; x_wconf 96'>lazy</span>
<span class='ocrx_word' id='word_1_15' title='bbox 211 654 272 684; x_wconf 96'>dog.</span>
</span>
</p>
</div>
</div>
</body>
</html>
"""
    page = slist.thread.get_page(id=1)
    page.import_hocr(hocr)
    set_text_in_mainloop(slist, 1, page.text_layer)

    mlp = GLib.MainLoop()
    slist.save_hocr(
        path=temp_txt.name,
        list_of_pages=[slist.data[0][2]],
        finished_callback=lambda response: mlp.quit(),
    )
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()

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
  <div class='ocr_page' id='page_1' title='bbox 0 0 708 1054'>
   <div class='ocr_carea' id='block_1_1' title='bbox 87 578 328 685'>
    <p class='ocr_par' id='par_1_1' title='bbox 87 578 328 609'>
     <span class='ocr_line' id='line_1_1' title='bbox 87 578 328 609; baseline 0.01 -7; textangle 0'>
      <span class='ocrx_word' id='word_1_1' title='bbox 87 578 143 602; x_wconf 96'>The1</span>
      <span class='ocrx_word' id='word_1_2' title='bbox 154 578 231 609; x_wconf 96'>quick1</span>
      <span class='ocrx_word' id='word_1_3' title='bbox 241 578 328 602; x_wconf 96'>brown1</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_2' title='bbox 639 814 708 1054'>
    <p class='ocr_par' id='par_1_2' title='bbox 639 814 708 1054'>
     <span class='ocr_line' id='line_1_2' title='bbox 639 814 670 1053; textangle 90'>
      <span class='ocrx_word' id='word_1_4' title='bbox 639 998 663 1053; x_wconf 96'>The2</span>
      <span class='ocrx_word' id='word_1_5' title='bbox 639 911 670 987; x_wconf 96'>quick2</span>
      <span class='ocrx_word' id='word_1_6' title='bbox 639 814 664 900; x_wconf 96'>brown2</span>
     </span>
    </p>
   </div>
   <div class='ocr_carea' id='block_1_3' title='bbox 87 578 328 685'>
    <p class='ocr_par' id='par_1_3' title='bbox 87 578 328 685'>
     <span class='ocr_header' id='header_1_1' title='bbox 88 578 328 609; baseline 0 -7'>
      <span class='ocrx_word' id='word_1_7' title='bbox 88 578 143 602; x_wconf 96'>The</span>
      <span class='ocrx_word' id='word_1_8' title='bbox 154 578 230 609; x_wconf 96'>quick</span>
      <span class='ocrx_word' id='word_1_9' title='bbox 241 578 328 602; x_wconf 96'>brown</span>
     </span>
     <span class='ocr_caption' id='caption_1_1' title='bbox 87 616 302 647; baseline 0 -7; textangle 0'>
      <span class='ocrx_word' id='word_1_10' title='bbox 87 616 130 640; x_wconf 96'>fox</span>
      <span class='ocrx_word' id='word_1_11' title='bbox 139 616 228 647; x_wconf 96'>jumps</span>
      <span class='ocrx_word' id='word_1_12' title='bbox 239 622 302 640; x_wconf 96'>over</span>
     </span>
     <span class='ocr_footer' id='footer_1_1' title='bbox 87 654 272 685; baseline -0.005 -7'>
      <span class='ocrx_word' id='word_1_13' title='bbox 87 655 132 678; x_wconf 96'>the</span>
      <span class='ocrx_word' id='word_1_14' title='bbox 144 654 201 685; x_wconf 96'>lazy</span>
      <span class='ocrx_word' id='word_1_15' title='bbox 211 654 272 684; x_wconf 96'>dog.</span>
     </span>
    </p>
   </div>
  </div>
 </body>
</html>
"""
    assert (
        subprocess.check_output(["cat", temp_txt.name], text=True) == hocr
    ), "saved hOCR"

    #########################

    clean_up_files(slist.thread.db_files)
