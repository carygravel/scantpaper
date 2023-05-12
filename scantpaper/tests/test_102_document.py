import glob
import os
import subprocess
import gi
from document import DocThread
from dialog.scan import Scan
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import logging
import tempfile
import pytest


def monitor_multiple(thread, uid_list):
    "helper function to save calls to monitor()"
    for uid in uid_list:
        thread.monitor(uid, block=True)


def test_1():

    # Gscan2pdf.Translation.set_domain('gscan2pdf')


    # logger = Log.Log4perl.get_logger
    # Gscan2pdf.Document.setup(logger)


    thread = DocThread()
    thread.start()

    with pytest.raises(FileNotFoundError):
        thread.do_get_file_info("test2.tif")

    subprocess.run(["touch","test.tif"])
    with pytest.raises(RuntimeError):
        thread.do_get_file_info("test.tif")

    subprocess.run(["convert","rose:","test.tif"])# Create test image
    info = {
        'format': 'Tagged Image File Format',
        'width': ['70'],
        'height': ['46'],
        'pages': 1,
        'path': 'test.tif',
        }
    assert thread.do_get_file_info("test.tif") == info, "do_get_file_info"

    def get_file_info_callback(response):
        assert response.process == "get_file_info", "get_file_info_finished_callback"
        print(f"get_file_info_callback {response}")
        assert response.info == info, "get_file_info"

    print(f"before thread.get_file_info")
    uid = thread.get_file_info("test.tif", finished_callback=get_file_info_callback)
    print(f"before monitor_multiple {uid}")
    monitor_multiple(thread, [uid, uid, uid, uid])

    for fname in ["test.tif"]:
        os.remove(fname)
#     assert False

#     slist  = Document()
#     window = Gtk.Window()
#     dialog = Scan(
#     title           = 'title',
#     transient_for = window,
#     document      = slist,
#     # logger        = logger,
#   ),    # dir for temporary files
#     dir = tempfile.TemporaryDirectory()
#     slist.set_dir(dir)

#     def anonymous_01():
#         clipboard = slist.copy_selection(True)
#         slist.paste_selection( clipboard, '0', 'after', True )               # copy-paste page 1->2
#         assert f"{slist}->{data}[0][2]{filename}"!=             f"{slist}->{data}[1][2]{filename}",             'different filename'
#         assert f"{slist}->{data}[0][2]{uuid}"!=             f"{slist}->{data}[1][2]{uuid}", 'different uuid'
#         assert slist["data"][1][0]== 2, 'new page is number 2'
#         rows = slist.get_selected_indices()
#         assert rows== [], 'pasted page selected'
#         dialog.page_number_start=3
#         clipboard = slist.cut_selection()
#         assert len(clipboard)-1==       0, 'cut 1 page to clipboard'
#         assert len( slist["data"] )-1== 0, '1 page left in list'
#         # TODO =                 "Don't know how to trigger update of page-number-start "               + "from Document"
#         # TODO: :
            
#         #     assert dialog.page_number_start== 2,               'page-number-start after cut'

#         slist.paste_selection( clipboard, '0', 'before' )               # paste page before 1
#         assert f"{slist}->{data}[0][2]{uuid}"==             clipboard[0][2]["uuid"],             'cut page pasted at page 1'
#         assert slist["data"][0][0]== 1, 'cut page renumbered to page 1'
#         rows = slist.get_selected_indices()
#         assert rows== [],             'pasted page not selected, as parameter not TRUE'
#         assert dialog.page_number_start== 3,           'page-number-start after paste'
#         slist.select( 0, 1 )
#         rows = slist.get_selected_indices()
#         assert rows== [        0, 1 ], 'selected all pages'
#         slist.delete_selection()
#         assert len( slist["data"] )-1== -1, 'deleted all pages'

#         # TODO/FIXME: test drag-and-drop callbacks for move

#         # TODO/FIXME: test drag-and-drop callbacks for copy

#         Gtk.main_quit()


#     slist.import_files(    paths             = [    'test.tif'],    finished_callback = anonymous_01 )
#     Gtk.main()

# #########################

#     os.remove(['test.tif']+glob.glob(f"{dir}/*"))  
#     os.rmdir(dir) 
#     Gscan2pdf.Document.quit()
