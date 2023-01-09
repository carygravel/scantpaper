import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk
import tempfile
import PythonMagick
from imageview import ImageView, Dragger, Selector, SelectorDragger, Tool
import pytest
import re


def test_1():


    
    


#########################

    view = ImageView()
    assert isinstance( view, ImageView )
    assert isinstance(
    view.get_tool(),
    Dragger
),     'get_tool() defaults to dragger'

    tmp   = tempfile.NamedTemporaryFile( suffix = '.png' ).name
    image = PythonMagick.Image('rose:')
    image.write( tmp )
    signal=None
    def anonymous_01( widget, x, y ):
        
        view.signal_handler_disconnect(signal)
        if not (view.scale_factor>1) :
            
            assert x== 0,  'emitted offset-changed signal x'
            assert y== 11, 'emitted offset-changed signal y'



    signal = view.connect(
    'offset-changed' , anonymous_01 
)
    view.set_pixbuf( GdkPixbuf.Pixbuf.new_from_file(tmp), True )
    if view.get_scale_factor()<=1:
        viewport = view.get_viewport()
        assert viewport.x == 0, 'get_viewport x'
        assert viewport.y == pytest.approx(-12, 0.001), 'get_viewport y'
        assert viewport.width == pytest.approx(70, 0.001), 'get_viewport width'
        assert viewport.height == pytest.approx(70, 0.001), 'get_viewport height'


    if False :
    
        assert isinstance( view.get_draw_rect(), Gtk.Gdk.Rectangle )
        assert view.get_check_colors(), 'get_check_colors()'


    assert isinstance( view.get_pixbuf(), GdkPixbuf.Pixbuf ), 'get_pixbuf()'
    assert view.get_pixbuf_size()== { "width" : 70, "height" : 46 },     'get_pixbuf_size'
    allocation = view.get_allocation()
    assert allocation.x== -1,     'get_allocation x'
    assert allocation.y== -1,     'get_allocation y'
    assert allocation.width== 1,     'get_allocation width'
    assert allocation.height== 1,     'get_allocation height'

    assert view.get_zoom() == pytest.approx( 0.01428 * view.get_scale_factor(), 0.001 ), 'get_zoom()'

    def anonymous_02( widget, zoom ):
        
        view.signal_handler_disconnect(signal)
        assert zoom== 1, 'emitted zoom-changed signal'


    signal = view.connect(    'zoom-changed' , anonymous_02 )
    view.set_zoom(1)

    def anonymous_03( widget, selection ):
        
        view.signal_handler_disconnect(signal)
        assert selection==             { "x" : 10, "y" : 10, "width" : 10, "height" : 10 },             'emitted selection-changed signal'


    signal = view.connect(    'selection-changed' , anonymous_03 )
    view.set_selection(    { "x" : 10, "y" : 10, "width" : 10, "height" : 10 } )
    assert view.get_selection()==     { "x" : 10, "y" : 10, "width" : 10, "height" : 10 },     'get_selection'

    def anonymous_04( widget, tool ):
        
        view.signal_handler_disconnect(signal)
        assert isinstance(            tool,            Selector        ),             'emitted tool-changed signal'


    signal = view.connect(    'tool-changed' , anonymous_04 )
    view.set_tool(Selector(view))

    view.set_selection(
    { "x" : -10, "y" : -10, "width" : 20, "height" : 20 } )
    assert view.get_selection()==     { "x" : 0, "y" : 0, "width" : 10, "height" : 10 },     'selection cannot overlap top left border'

    view.set_selection(
    { "x" : 10, "y" : 10, "width" : 80, "height" : 50 } )
    assert view.get_selection()==     { "x" : 10, "y" : 10, "width" : 60, "height" : 36 },     'selection cannot overlap bottom right border'

    view.set_resolution_ratio(2)
    assert view.get_resolution_ratio()== 2, 'get/set_resolution_ratio()'

    if False :
    
        assert Gtk.ImageView.Zoom.get_min_zoom() <           Gtk.ImageView.Zoom.get_max_zoom(), 'Ensure that the gtkimageview.zooms_* functions are present and work as expected.'
        assert  view.get_black_bg() is not None, 'get_black_bg()'
        assert  view.get_show_frame() is not None, 'get_show_frame()'
        assert  view.get_interpolation() is not None, 'get_interpolation()'
        assert  view.get_show_cursor() is not None, 'get_show_cursor()'


    # A TypeError is raised when set_pixbuf() is called with something that is not a pixbuf.
    with pytest.raises(TypeError):
        view.set_pixbuf( 'Hi mom!', True )
 

    view.set_pixbuf( None, True )
    assert  view.get_pixbuf() is None, 'correctly cleared pixbuf'
    assert view.get_viewport()==     { "x" : 0, "y" : 0, "width" : 1, "height" : 1 },     'correctly cleared viewport'

    try :
        view.set_pixbuf( None, False )
        assert True, 'correctly cleared pixbuf2'

    except :
        assert False, 'correctly cleared pixbuf2'


    if False :
    
        assert notview.get_draw_rect(), 'correctly cleared draw rectangle'
        view.size_allocate( Gdk.Rectangle( 0, 0, 100, 100 ) )
        view.set_pixbuf(
        Gdk.Pixbuf(
            Gdk.colormap_get_system(),
            False, 8, 50, 50
        )
    )
        rect = view.get_viewport()
        assert          (
                  rect.x() == 0 and rect.y() == 0
              and rect.width() == 50
              and rect.height() == 50
        ),         'Ensure that getting the viewport of the view works as expected.'
        can_ok( view, ["get_check_colors"] )
        rect = view.get_draw_rect()
        assert          (
                  rect.x() == 25 and rect.y() == 25
              and rect.width() == 50
              and rect.height() == 50
        ),         'Ensure that getting the draw rectangle works as expected.'
        view.set_pixbuf(
        Gdk.Pixbuf(
            Gdk.colormap_get_system(),
            False, 8, 200, 200
        )
    )
        view.set_zoom(1)
        view.set_offset( 0, 0 )
        rect = view.get_viewport()
        assert  ( rect.x() == 0 and rect.y() == 0 ),         'Ensure that setting the offset works as expected.'
        view.set_offset( 100, 100, True )
        rect = view.get_viewport()
        assert  ( rect.x() == 100 and rect.y() == 100 ),         'Ensure that setting the offset works as expected.'
        view.set_transp( 'color', 0xff0000 )
        ( col1, col2 ) = view.get_check_colors()
        assert          ( col1 == 0xff0000 and col2 == 0xff0000 ),         'Ensure that setting the views transparency settings works as expected.'
        view.set_transp('grid')
        assert  (GObject.TypeModule.list_values('Gtk3::ImageView::Transp') is not None),         'Check GtkImageTransp enum.'

