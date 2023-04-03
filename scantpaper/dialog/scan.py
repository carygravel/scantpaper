from gi.repository import Gdk, Gtk, GObject
import re
import sane
from copy import deepcopy
# import GooCanvas2
from comboboxtext import ComboBoxText
from dialog import Dialog
from scanner.options import Options
from scanner.profile import Profile
import gettext  # For translations

# from translation import __
# easier to extract strings with xgettext
_ = gettext.gettext

SANE_NAME_SCAN_TL_X   = "tl-x"
SANE_NAME_SCAN_TL_Y   = "tl-y"
SANE_NAME_SCAN_BR_X   = "br-x"
SANE_NAME_SCAN_BR_Y   = "br-y"
SANE_NAME_PAGE_HEIGHT = "page-height"
SANE_NAME_PAGE_WIDTH  = "page-width"
PAPER_TOLERANCE  = 1
OPTION_TOLERANCE = 0.001
INFINITE         = -1
MAX_PAGES         = 9999
MAX_INCREMENT     = 99
DOUBLE_INCREMENT  = 2
CANVAS_SIZE       = 200
CANVAS_BORDER     = 10
CANVAS_POINT_SIZE = 10
CANVAS_MIN_WIDTH  = 1
NO_INDEX          = -1

# start page
start=None
( d_sane, logger )=(None,None)
# GObject.TypeModule.register_enum( 'Gscan2pdf::Dialog::Scan::Side',
#         ["facing","reverse"] )
# GObject.TypeModule.register_enum( 'Gscan2pdf::Dialog::Scan::Sided',
#         ["single","double"] )
    
class Scan(Dialog):

    __gsignals__={
        'new-scan':(GObject.SignalFlags.RUN_FIRST,None,( str,int,float,float, )),
        'changed-device':(GObject.SignalFlags.RUN_FIRST,None,(str,)),
        'changed-device-list':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'changed-num-pages':(GObject.SignalFlags.RUN_FIRST,None,(int,)),
        'changed-page-number-start':(GObject.SignalFlags.RUN_FIRST,None,(int,)),
        'changed-page-number-increment':(GObject.SignalFlags.RUN_FIRST,None,(int,)),
        'changed-side-to-scan':(GObject.SignalFlags.RUN_FIRST,None,(str,)),
        'changed-scan-option':(GObject.SignalFlags.RUN_FIRST,None,( object,object,object, )),
        'changed-option-visibility':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'changed-current-scan-options':(GObject.SignalFlags.RUN_FIRST,None,( object,str, )),
        'reloaded-scan-options':(GObject.SignalFlags.RUN_FIRST,None,()),
        'changed-profile':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'added-profile':(GObject.SignalFlags.RUN_FIRST,None,( object,object, )),
        'removed-profile':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'changed-paper':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'changed-paper-formats':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'started-process':(GObject.SignalFlags.RUN_FIRST,None,(object,)),
        'changed-progress':(GObject.SignalFlags.RUN_FIRST,None,( object,object, )),
        'finished-process':(GObject.SignalFlags.RUN_FIRST,None,(str,)),
        'process-error':(GObject.SignalFlags.RUN_FIRST,None,( str,str, )),
        'clicked-scan-button':(GObject.SignalFlags.RUN_FIRST,None,()),
    }
    device=GObject.Property(type=str,default="",nick='Device',blurb='Device name')
    device_list=GObject.Property(type=object,nick='Device list',blurb='Array of hashes of available devices')
    dir=GObject.Property(type=object,nick='Directory',blurb='Directory in which to store scans')
    logger=GObject.Property(type=object,nick='Logger',blurb='Log::Log4perl::get_logger object')
    profile=GObject.Property(type=object,nick='Profile',blurb='Name of current profile')
    paper=GObject.Property(type=str,default="",nick='Paper',blurb='Name of currently selected paper format')
    paper_formats=GObject.Property(type=object,nick='Paper formats',blurb='Hash of arrays defining paper formats, e.g. A4, Letter, etc.')
    num_pages=GObject.Property(type=int,minimum=0,maximum=MAX_PAGES,default=1,nick='Number of pages',blurb='Number of pages to be scanned')
    max_pages=GObject.Property(type=int,minimum=-1,maximum=MAX_PAGES,default=0,nick='Maximum number of pages',blurb='Maximum number of pages that can be scanned with current page-number-start and page-number-increment')
    page_number_start=GObject.Property(type=int,minimum=1,maximum=MAX_PAGES,default=1,nick='Starting page number',blurb='Page number of first page to be scanned')
    page_number_increment=GObject.Property(type=int,minimum=-MAX_INCREMENT,maximum=MAX_INCREMENT,default=1,nick='Page number increment',blurb='Amount to increment page number when scanning multiple pages')
    # side_to_scan=GObject.Property(type=GObject.GEnum,default='facing',nick='Side to scan',blurb='Either facing or reverse')
    side_to_scan = GObject.Property(
        type=str, default="facing", nick="Side to scan", blurb="Either facing or reverse"
    )
    available_scan_options=GObject.Property(type=object,nick='Scan options available',blurb='Scan options currently available, whether active, selected, or not')
    current_scan_options=GObject.Property(type=object,nick='Current scan options',blurb='Scan options making up current profile')
    visible_scan_options=GObject.Property(type=object,nick='Visible scan options',blurb='Hash of scan options to show or hide from the user')
    progress_pulse_step=GObject.Property(type=float,minimum=0.0,maximum=1.0,default=0.1,nick='Progress pulse step',blurb='Pulse step of progress bar')
    allow_batch_flatbed=GObject.Property(type=bool,default=False,nick='Allow batch scanning from flatbed',blurb='Allow batch scanning from flatbed')
    adf_defaults_scan_all_pages=GObject.Property(type=bool,default=True,nick='Select # pages = all on selecting ADF',blurb='Select # pages = all on selecting ADF')
    reload_recursion_limit=GObject.Property(type=int,minimum=0,maximum=MAX_INCREMENT,default=0,nick='Reload recursion limit',blurb='More reloads than this are considered infinite loop')
    num_reloads=GObject.Property(type=int,minimum=0,maximum=MAX_INCREMENT,default=0,nick='Number of reloads',blurb='To compare against reload-recursion-limit')
    document=GObject.Property(type=object,nick='Document',blurb='Gscan2pdf::Document for new scans')
    cursor=GObject.Property(type=object,nick='Cursor',blurb='name of current cursor')
    ignore_duplex_capabilities=GObject.Property(type=bool,default=False,nick='Ignore duplex capabilities',blurb='Ignore duplex capabilities')

    # sided=GObject.Property(type=GObject.GEnum,default='single',nick='Sided',blurb='Either single or double')
    @GObject.Property(type=str, default="single", nick="Sided", blurb="Either single or double")
    def sided(self):
        return self.sided

    @sided.setter
    def sided(self, newval):
        self.sided = newval
        widget = self.buttons
        if newval == 'double' :
            widget = self.buttond
        else :
            # selecting single-sided also selects facing page.
            self.side_to_scan='facing'
        widget.set_active(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.connect("show",show)

        vbox = self.get_content_area()
        # d_sane = gettext.translation('sane-backends')
        self._add_device_combobox(vbox)

    # Notebook to collate options

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        vbox.pack_start( self.notebook, True, True, 0 )

    # Notebook page 1

        scwin = Gtk.ScrolledWindow()
        _ = gettext.gettext
        self.notebook.append_page( child=scwin, tab_label=Gtk.Label( label=_('Page Options') ) )
        scwin.set_policy( Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC )
        vbox1 = Gtk.VBox()
        # self.vbox = vbox1
        border_width = self.get_style_context().get_border(Gtk.StateFlags.NORMAL).left#._get('content-area-border')
        vbox1.set_border_width(border_width)
        scwin.add(vbox1)

    # Frame for # pages

        self.framen = Gtk.Frame( label=_('# Pages') )
        vbox1.pack_start( self.framen, False, False, 0 )
        vboxn = Gtk.VBox()
        vboxn.set_border_width(border_width)
        self.framen.add(vboxn)

    # the first radio button has to set the group,
    # which is undef for the first button
    # All button

        bscanall =       Gtk.RadioButton.new_with_label_from_widget( None, _('All') )
        bscanall.set_tooltip_text( _('Scan all pages') )
        vboxn.pack_start( bscanall, True, True, 0 )
        def do_clicked_scan_all(_data):
            if bscanall.get_active() :
                self.num_pages=0


        bscanall.connect(        'clicked' , do_clicked_scan_all     )

    # Entry button

        hboxn = Gtk.HBox()
        vboxn.pack_start( hboxn, True, True, 0 )
        bscannum =       Gtk.RadioButton.new_with_label_from_widget( bscanall, "#:" )
        bscannum.set_tooltip_text( _('Set number of pages to scan') )
        hboxn.pack_start( bscannum, False, False, 0 )

    # Number of pages

        spin_buttonn = Gtk.SpinButton.new_with_range( 1, MAX_PAGES, 1 )
        spin_buttonn.set_tooltip_text( _('Set number of pages to scan') )
        hboxn.pack_end( spin_buttonn, False, False, 0 )
        def do_clicked_scan_number(_data):
            if bscannum.get_active() :
                self.num_pages=spin_buttonn



        bscannum.connect(        'clicked' , do_clicked_scan_number     )
        def anonymous_03( widget, value ):
            
            if value == 0 :
                bscanall.set_active(True)
 
            else :
                # if spin button is already $value, but pages = all is selected,
                # then the callback will not fire to activate # pages, so doing
                # it here

                bscannum.set_active(True)
                spin_buttonn.set_value(value)


            # Check that there is room in the list for the number of pages

            self.update_num_pages()


        self.connect(
        'changed-num-pages' , anonymous_03 
    )
        self.connect(
        'changed-scan-option' , self._changed_scan_option_callback,
        bscannum
    )

    # Actively set a radio button to synchronise GUI and properties

        if self.num_pages > 0 :
            bscannum.set_active(True)
 
        else :
            bscanall.set_active(True)


    # vbox for duplex/simplex page numbering in order to be able to show/hide
    # them together.

        self.vboxx = Gtk.VBox()
        vbox1.pack_start( self.vboxx, False, False, 0 )

    # Switch between basic and extended modes

        hbox  = Gtk.HBox()
        label = Gtk.Label( label=_('Extended page numbering') )
        hbox.pack_start( label, False, False, 0 )
        self.checkx = Gtk.Switch()
        hbox.pack_end( self.checkx, False, False, 0 )
        self.vboxx.pack_start( hbox, False, False, 0 )

    # Frame for extended mode

        self.framex = Gtk.Frame( label=_('Page number') )
        self.vboxx.pack_start( self.framex, False, False, 0 )
        vboxx = Gtk.VBox()
        vboxx.set_border_width(border_width)
        self.framex.add(vboxx)

    # SpinButton for starting page number

        hboxxs = Gtk.HBox()
        vboxx.pack_start( hboxxs, False, False, 0 )
        labelxs = Gtk.Label( label=_('Start') )
        hboxxs.pack_start( labelxs, False, False, 0 )
        spin_buttons = Gtk.SpinButton.new_with_range( 1, MAX_PAGES, 1 )
        hboxxs.pack_end( spin_buttons, False, False, 0 )
        def anonymous_04():
            self.page_number_start=spin_buttons
            self.update_start_page()


        spin_buttons.connect(
        'value-changed' , anonymous_04 
    )
        def anonymous_05( widget, value ):
            
            spin_buttons.set_value(value)
            slist = self.document
            if   (slist is None) :
                return
            self.max_pages=slist


        self.connect(
        'changed-page-number-start' , anonymous_05 
    )

    # SpinButton for page number increment

        hboxi = Gtk.HBox()
        vboxx.pack_start( hboxi, False, False, 0 )
        labelxi = Gtk.Label( label=_('Increment') )
        hboxi.pack_start( labelxi, False, False, 0 )
        spin_buttoni =       Gtk.SpinButton.new_with_range( -MAX_INCREMENT, MAX_INCREMENT, 1 )
        spin_buttoni.set_value( self.page_number_increment )
        hboxi.pack_end( spin_buttoni, False, False, 0 )
        def anonymous_06():
            value = spin_buttoni.get_value()
            if value == 0 :
                value = -self.page_number_increment
            spin_buttoni.set_value(value)
            self.page_number_increment=value


        spin_buttoni.connect(
        'value-changed' , anonymous_06 
    )
        def anonymous_07( widget, value ):
            
            spin_buttoni.set_value(value)
            slist = self.document
            if   (slist is None) :
                return
            self.max_pages=slist


        self.connect(
        'changed-page-number-increment' , anonymous_07 
    )

    # Setting this here to fire callback running update_start

        spin_buttons.set_value( self.page_number_start )

        def anonymous_08():
            """    # Callback on changing number of pages
"""
            self.num_pages=spin_buttonn
            bscannum.set_active(True)    # Set the radiobutton active


        spin_buttonn.connect(
        'value-changed' , anonymous_08 
    )

    # Frame for standard mode

        self.frames = Gtk.Frame( label=_('Source document') )
        self.vboxx.pack_start( self.frames, False, False, 0 )
        vboxs = Gtk.VBox()
        vboxs.set_border_width(border_width)
        self.frames.add(vboxs)

    # Single sided button

        self.buttons = Gtk.RadioButton.new_with_label_from_widget( None,
        _('Single sided') )
        self.buttons.set_tooltip_text( _('Source document is single-sided') )
        vboxs.pack_start( self.buttons, True, True, 0 )
        def anonymous_09():
            spin_buttoni.set_value(1)
            self.sided=self


        self.buttons.connect(
        'clicked' , anonymous_09 
    )

    # Double sided button

        self.buttond =       Gtk.RadioButton.new_with_label_from_widget( self.buttons,
        _('Double sided') )
        self.buttond.set_tooltip_text( _('Source document is double-sided') )
        vboxs.pack_start( self.buttond, False, False, 0 )

    # Facing/reverse page button

        hboxs = Gtk.HBox()
        vboxs.pack_start( hboxs, True, True, 0 )
        labels = Gtk.Label( label=_('Side to scan') )
        hboxs.pack_start( labels, False, False, 0 )
        self.combobs = ComboBoxText()
        for text in          ( _('Facing'), _('Reverse') ) :
            self.combobs.append_text(text)

        def anonymous_10():
            self.buttond.set_active(True)    # Set the radiobutton active
            self.side_to_scan=self


        self.combobs.connect(        'changed' , anonymous_10     )
        def anonymous_11( widget, value ):
            
            self.page_number_increment=value
            if value == 'facing' :
                self.num_pages=0



        self.connect(        'changed-side-to-scan' , anonymous_11     )
        self.combobs.set_tooltip_text(_('Sets which side of a double-sided document is scanned') )
        self.combobs.set_active(0)

    # Have to do this here because setting the facing combobox switches it

        self.buttons.set_active(True)
        hboxs.pack_end( self.combobs, False, False, 0 )

        def anonymous_12():
            "Have to put the double-sided callback here to reference page side"
            spin_buttoni.set_value(
                    
                DOUBLE_INCREMENT if self.combobs.get_active()==0 
                else -DOUBLE_INCREMENT
            )


        self.buttond.connect(
        'clicked' , anonymous_12 
    )

    # Have to put the extended pagenumber checkbox here
    # to reference simple controls

        self.checkx.connect(
        'notify::active' , _extended_pagenumber_checkbox_callback,
        [
        self, spin_buttoni ]
    )

    # Scan profiles

        self.current_scan_options = Profile()
        framesp = Gtk.Frame( label=_('Scan profiles') )
        vbox1.pack_start( framesp, False, False, 0 )
        vboxsp = Gtk.VBox()
        vboxsp.set_border_width(border_width)
        framesp.add(vboxsp)
        self.combobsp                = ComboBoxText()
        def anonymous_13():
            self.num_reloads = 0    # num-reloads is read-only
            self.profile=self


        self.combobsp_changed_signal = self.combobsp.connect(
        'changed' , anonymous_13 
    )
        vboxsp.pack_start( self.combobsp, False, False, 0 )
        hboxsp = Gtk.HBox()
        vboxsp.pack_end( hboxsp, False, False, 0 )

    # Save button

        vbutton = Gtk.Button.new_from_stock('gtk-save')
        vbutton.connect( 'clicked' , _save_profile_callback, self )
        hboxsp.pack_start( vbutton, True, True, 0 )

    # Edit button

        ebutton = Gtk.Button.new_from_stock('gtk-edit')
        ebutton.connect( 'clicked' , _edit_profile_callback, self )
        hboxsp.pack_start( ebutton, False, False, 0 )

    # Delete button

        dbutton = Gtk.Button.new_from_stock('gtk-delete')
        def anonymous_14():
            self.remove_profile( self.combobsp.get_active_text() )


        dbutton.connect(
        'clicked' , anonymous_14 
    )
        hboxsp.pack_start( dbutton, False, False, 0 )
        def anonymous_15():
            self.emit('clicked-scan-button')
            self.scan()


        def anonymous_16():
            self.hide()

        ( self.scan_button ) = self.add_actions([(
        _('Scan'),
        anonymous_15) ,(
        'gtk-close',
        anonymous_16) ]
    )

    # initialise stack of uuids - needed for cases where setting a profile
    # requires several reloads, and therefore reapplying the same profile
    # several times. Tested by t/06198_Dialog_Scan_Image_Sane.t

        self.setting_profile              = []
        self.setting_current_scan_options = []
        self.cursor='default'


    def _add_device_combobox( self, vbox ) :
    
        self.hboxd = Gtk.HBox()
        labeld = Gtk.Label( label=_('Device') )
        self.hboxd.pack_start( labeld, False, False, 0 )
        self.combobd = ComboBoxText()
        self.combobd.append_text( _('Rescan for devices') )
        def anonymous_17():
            index       = self.combobd.get_active()
            device_list = self.device_list
            if index > len(device_list)-1 :
                self.combobd.hide()
                labeld.hide()
                self.device=None                       # to make sure that the device is reloaded
                self.get_devices()
 
            elif index > NO_INDEX :
                self.device=device_list



        self.combobd_changed_signal = self.combobd.connect(
        'changed' , anonymous_17 
    )
        def anonymous_18( self, device ):
            
            device_list = self.device_list
            if  (device is not None) and device != "" :
                for _ in                  device_list  :
                    if _["name"] == device :
                        self.combobd.set_active_by_text( _["label"] )
                        self.scan_options(device)
                        return


 
            else :
                self.combobd.set_active(NO_INDEX)



        self.connect(
        'changed-device' , anonymous_18 
    )
        self.combobd       .set_tooltip_text( _('Sets the device to be used for the scan') )
        self.hboxd.pack_end( self.combobd, False, False, 0 )
        vbox.pack_start( self.hboxd, False, False, 0 )
        return









    def _set_side_to_scan( self, name, newval ) :
        """Clone current profile, display list of options, allowing user to delete those
not required, and then to cancel or accept the changes.
"""    
        self[name] = newval
        self.emit( 'changed-side-to-scan', newval )
        self.combobs.set_active(    0 if newval=='facing'  else 1 )
        slist = self.document
        if  (slist is not None) :
            possible = slist.pages_possible(
            self.page_number_start,
            self.page_number_increment
        )
            requested = self.num_pages
            if possible != INFINITE            and ( requested == 0 or requested > possible )         :
                self.num_pages=possible
                self.max_pages=possible


        return


    def SET_PROPERTY( self, pspec, newval ) :
    
        name   = pspec.get_name()
        oldval = self.get(name)

    # Have to set logger separately as it has already been set in the subclassed
    # widget

        if name == 'logger' :
            logger = newval
            logger.debug('Set logger in Gscan2pdf::Dialog::Scan')
            self[name] = newval
 
        elif _new_val( oldval, newval ) :
            msg=None
            if  (logger is not None) :
                msg =                 f" setting {name} from "               + Dialog.dump_or_stringify(oldval) + ' to '               + Dialog.dump_or_stringify(newval)
                logger.debug(f"Started{msg}")

            callback = False
            if name=='allow_batch_flatbed':
                self._set_allow_batch_flatbed( name, newval )

            elif name=='available_scan_options':
                self._set_available_scan_options( name, newval )

            elif name=='cursor':
                self[name] = newval
                self.set_cursor(newval)

            elif name=='device':
                self[name] = newval
                self.set_device(newval)
                self.emit( 'changed-device', newval )

            elif name=='device_list':
                self[name] = newval
                self.set_device_list(newval)
                self.emit( 'changed-device-list', newval )

            elif name=='document':
                self[name] = newval

                # Update the start spinbutton if the page number is been edited.

                slist = self.document
                if  (slist is not None) :
                    def anonymous_22():
                        self.update_start_page()

                    slist.get_model().connect(
                        'row-changed' , anonymous_22  )


            elif name=='ignore_duplex_capabilities':
                self[name] = newval
                self._flatbed_or_duplex_callback()

            elif name=='num_pages':
                self._set_num_pages( name, newval )

            elif name=='page_number_start':
                self[name] = newval
                self.emit( 'changed-page-number-start', newval )

            elif name=='page_number_increment':
                self[name] = newval
                self.emit( 'changed-page-number-increment', newval )

            elif name=='side_to_scan':
                self._set_side_to_scan( name, newval )

            elif name=='paper':
                if  (newval is not None) :
                    for _ in                      self.ignored_paper_formats  :
                        if _ == newval :
                            if  (logger is not None) :
                                logger.info(
                                    f"Ignoring unsupported paper {newval}")
                                logger.debug(f"Finished{msg}")

                            return



                callback = True
                signal=None
                def anonymous_23():
                    self.disconnect(signal)
                    paper =   newval if (newval is not None)  else _('Manual')
                    retval =                           self.combobp.set_active_by_text(paper)
                    logger.debug(
                            f"Widget update to {paper} returned {retval}")
                    if  (logger is not None) :
                        logger.debug(f"Finished{msg}")



                signal = self.connect(
                    'changed-paper' , anonymous_23 
                )
                self.set_paper(newval)

            elif name=='paper_formats':
                self[name] = newval
                self.set_paper_formats(newval)
                self.emit( 'changed-paper-formats', newval )

            elif name=='profile':
                callback = True
                signal=None
                def anonymous_24():
                    self.disconnect(signal)
                    self.combobsp.set_active_by_text(newval)
                    if  (logger is not None) :
                        logger.debug(f"Finished{msg}")



                signal = self.connect(
                    'changed-profile' , anonymous_24 
                )
                self.set_profile(newval)

            elif name=='visible_scan_options':
                self[name] = newval
                self.emit( 'changed-option-visibility', newval )

            else :
                self[name] = newval

            if  (logger is not None) and not callback :
                logger.debug(f"Finished{msg}")


        return




    def _flatbed_or_duplex_callback(self) :
    
        options = self.available_scan_options
        if  (options is not None) :
            if options.flatbed_selected()            or ( options.can_duplex()
                and not self.ignore_duplex_capabilities )         :
                self.vboxx.hide()
 
            else :
                self.vboxx.show()


        return


    def _changed_scan_option_callback( self, name, value, uuid, bscannum ) :
    
        options = self.available_scan_options
        if  (options is not None)        and  "name"  in options["source"]        and name == options["source"]["name"]     :
            if self.allow_batch_flatbed            or not options.flatbed_selected()         :
                self.framen.set_sensitive(True)
 
            else :
                bscannum.set_active(True)
                self.num_pages=1
                self.sided='single'
                self.framen.set_sensitive(False)

            if self.adf_defaults_scan_all_pages            and   re.search(r"(ADF|Automatic[ ]Document[ ]Feeder)",value,re.IGNORECASE|re.MULTILINE|re.DOTALL|re.VERBOSE)         :
                self.num_pages=0


        self._flatbed_or_duplex_callback()
        return


    def _set_allow_batch_flatbed( self, name, newval ) :
    
        self[name] = newval
        if newval :
            self.framen.set_sensitive(True)
 
        else :
            options = self.available_scan_options
            if  (options is not None) and options.flatbed_selected() :
                self.framen.set_sensitive(False)

            # emits changed-num-pages signal, allowing us to test
            # for $self->{framen}->set_sensitive(FALSE)

                self.num_pages=1


        return


    def _set_available_scan_options( self, name, newval ) :
    
        self[name] = newval
        if not self.allow_batch_flatbed and newval.flatbed_selected() :
            if self.num_pages != 1 :
                self.num_pages=1
            self.framen.set_sensitive(False)
 
        else :
            self.framen.set_sensitive(True)

        self._flatbed_or_duplex_callback()

    # reload-recursion-limit is read-only
    # Triangular number n + n-1 + n-2 + ... + 1 = n*(n+1)/2

        n = newval.num_options()
        self.reload_recursion_limit = n * ( n + 1 ) / 2
        self.emit('reloaded-scan-options')
        return


    def _set_num_pages( self, name, newval ) :
    
        options = self.available_scan_options
        if newval == 1        or self.allow_batch_flatbed        or (     (options is not None)
            and  "val"  in options["source"]
            and not options.flatbed_selected() )     :
            self[name] = newval
            self.current_scan_options.add_frontend_option( name, newval )
            self.emit( 'changed-num-pages', newval )

        return


    def show(self) :
    
        self.signal_chain_from_overridden()
        self.framex.hide()
        self._flatbed_or_duplex_callback()
        if  (self.combobp is not None)        and  (self.combobp.get_active_text is not None)()        and self.combobp.get_active_text() != _('Manual')     :
            self.hide_geometry( self.available_scan_options )

        self.set_cursor()
        return


    def set_device( self, device ) :
    
        if  (device is not None) and device != "" :
            o=None
            device_list = self.device_list
            if  (device_list is not None) :
                for _ in                  range(len(device_list)-1+1)    :
                    if device == device_list[_]["name"] :
                        o = _


            # Set the device dependent options after the number of pages
            #  to scan so that the source button callback can ghost the
            #  all button.
            # This then fires the callback, updating the options,
            #  so no need to do it further down.

                if  (o is not None) :
                    self.combobd.set_active(o)
 
                else :
                    self.emit( 'process-error', 'open_device',
                    _('Error: unknown device: %s') % (device)   )



        return


    def set_device_list( self, device_list ) :
    

    # Note any duplicate device names and delete if necessary

        seen={}
        i = 0
        while i < len(device_list) :
            seen[ device_list[i]["name"] ]+=1
            if seen[ device_list[i]["name"] ] > 1 :
                del(device_list[i])   
 
            else :
                i+=1



    # Note any duplicate model names and add the device if necessary

        seen=None
        for _ in          device_list  :
            if "model" not   in _ :
                _["model"] = _["name"]
            seen[ _["model"] ]+=1

        for _ in          device_list  :
            if  "vendor"  in _ :
                _["label"] = f"{_}->{vendor} {_}->{model}"
 
            else :
                _["label"] = _["model"]

            if seen[ _["model"] ] > 1 :
                _["label"] += f" on {_}->{name}"

        self.combobd.signal_handler_block( self.combobd_changed_signal )

    # Remove all entries apart from rescan

        num_rows = self.combobd.get_num_rows()
        while num_rows>1 :
            num_rows-=1
            self.combobd.remove(0)


    # read the model names into the combobox

        for _ in          range(len(device_list)-1+1)    :
            self.combobd.insert_text( _, device_list[_]["label"] )

        self.combobd.signal_handler_unblock( self.combobd_changed_signal )
        return


    def pack_widget( self, widget, data ) :
    
        ( options, opt, hbox, hboxp ) = len(data)
        if  (widget is not None) :

        # Add label for units

            if opt["unit"] != "UNIT_NONE" :
                text=None
                if  opt["unit"] =="UNIT_PIXEL":
                    text = _('pel')

                elif  opt["unit"] =="UNIT_BIT":
                    text = _('bit')

                elif  opt["unit"] =="UNIT_MM":
                    text = _('mm')

                elif  opt["unit"] =="UNIT_DPI":
                    text = _('ppi')

                elif  opt["unit"] =="UNIT_PERCENT":
                    text = _("%")

                elif  opt["unit"] =="UNIT_MICROSECOND":
                    text = _('μs')

                label = Gtk.Label(label=text)
                hbox.pack_end( label, False, False, 0 )

            self.option_widgets[ opt["name"] ] = widget
            if opt["type"] == "TYPE_BUTTON" or opt["max_values"] > 1 :
                hbox.pack_end( widget, True, True, 0 )
 
            else :
                hbox.pack_end( widget, False, False, 0 )

            widget.set_tooltip_text( d_sane.get( opt["desc"] ) )

        # Look-up to hide/show the box if necessary

            if self._geometry_option(opt) :
                self.geometry_boxes[ opt["name"] ] = hbox

            self.create_paper_widget( options, hboxp )
 
        else :
            logger.warn(f"Unknown type {opt}->{type}")

        return



    def _geometry_option( self, opt ) :
        """Return true if we have a valid geometry option
"""    
        return (
        ( opt["type"] == "TYPE_FIXED" or opt["type"] == "TYPE_INT" )           and           ( opt["unit"] == "UNIT_MM" or opt["unit"] == "UNIT_PIXEL" )           and (  
re.search(fr"^(?:{SANE_NAME_SCAN_TL_X}|{SANE_NAME_SCAN_TL_Y}|{SANE_NAME_SCAN_BR_X}|{SANE_NAME_SCAN_BR_Y}|{SANE_NAME_PAGE_HEIGHT}|{SANE_NAME_PAGE_WIDTH})$",opt["name"],re.MULTILINE|re.DOTALL|re.VERBOSE)
          )
    )


    def create_paper_widget( self, options, hboxp ) :
    

    # Only define the paper size once the rest of the geometry widgets
    # have been created

        if SANE_NAME_SCAN_BR_X  in self.geometry_boxes        and SANE_NAME_SCAN_BR_Y  in self.geometry_boxes        and SANE_NAME_SCAN_TL_X  in self.geometry_boxes        and SANE_NAME_SCAN_TL_Y  in self.geometry_boxes        and (   (options.by_name("page-height") is None) or SANE_NAME_PAGE_HEIGHT  in self.geometry_boxes ) and (   (options.by_name("page-width") is None) or SANE_NAME_PAGE_WIDTH  in self.geometry_boxes ) and  (self.combobp is None)     :

        # Paper list

            label = Gtk.Label( label=_('Paper size') )
            hboxp.pack_start( label, False, False, 0 )
            self.combobp = ComboBoxText()
            self.combobp.append_text( _('Manual') )
            self.combobp.append_text( _('Edit') )
            self.combobp           .set_tooltip_text( _('Selects or edits the paper size') )
            hboxp.pack_end( self.combobp, False, False, 0 )
            self.combobp.set_active(0)
            def anonymous_25():
                if   (self.combobp.get_active_text is None)() :
                    return
                if self.combobp.get_active_text() == _('Edit') :
                    self.edit_paper()
 
                elif self.combobp.get_active_text() == _('Manual') :
                    for _ in                                            ( "tl-x", "tl-y",
                            "br-x",   "br-y",
                            "page-height", "page-width"
                        )                     :
                        if  _  in self.geometry_boxes :
                            self.geometry_boxes[_].show_all()


                    self.paper=None
 
                else :
                    paper = self.combobp.get_active_text()
                    self.paper=paper



            self.combobp.connect(
            'changed' , anonymous_25 
        )

        # If the geometry is changed, unset the paper size,
        # if we are not setting a profile

            for _ in                        ( "tl-x", "tl-y",
                "br-x",   "br-y",
                "page-height", "page-width"
            )         :
                if  (options.by_name(_) is not None) :
                    widget = self.option_widgets[_]
                    def anonymous_26():
                        if not len( self.setting_current_scan_options )                            and   (self.paper is not None)                        :
                            self.paper=None



                    widget.connect(
                    'changed' , anonymous_26 
                )



        return


    def hide_geometry( self, options ) :
    
        for _ in                ( "tl-x", "tl-y",
            "br-x",   "br-y",
            "page-height", "page-width"
        )     :
            if  _  in self.geometry_boxes :
                self.geometry_boxes[_].hide()


        return


    def get_paper_by_geometry(self) :
    
        formats = self.paper_formats
        if   (formats is None) :
            return
        options = self.available_scan_options
        current = {
        "l" : options.by_name("tl-x")["val"],
        "t" : options.by_name("tl-y")["val"],
    }
        current["x"] = current["l"] + options.by_name("br-x")["val"]
        current["y"] = current["t"] + options.by_name("br-y")["val"]
        for  paper in          formats.keys()   :
            match = True
            for _ in             ["l","t","x","y"] :
                if formats[paper][_] != current[_] :
                    match = False
                    break


            if match :
                return paper

        return



    def update_options( self, new_options ) :
        """If setting an option triggers a reload, the widgets must be updated to reflect
the new options
"""    
        logger.debug( 'Sane->get_option_descriptor returned: ',
        Dumper(new_options) )
        loops = self.num_reloads
        loops+=1
        self.num_reloads = loops    # num-reloads is read-only
        limit = self.reload_recursion_limit
        if self.num_reloads > limit :
            logger.error(f"reload-recursion-limit ({limit}) exceeded.")
            self.emit(
            'process-error',
            'update_options',
            _(
'Reload recursion limit (%d) exceeded. Please file a bug, attaching a log file reproducing the problem.'
            ) % (limit) 
            
        )
            return


    # Clone the current scan options in case they are changed by the reload,
    # so that we can reapply it afterwards to ensure the same values are still
    # set.

        current_scan_options = deepcopy( self.current_scan_options )

    # walk the widget tree and update them from the hash

        num_dev_options = new_options.num_options()
        options         = self.available_scan_options
        for _ in          range(1,num_dev_options-1+1)      :
            if self._update_option(
                options.by_index(_),
                new_options.by_index(_)
            )         :
                return



    # This fires the reloaded-scan-options signal,
    # so don't set this until we have finished

        self.available_scan_options=new_options

    # Remove buttons from $current_scan_options to prevent buttons which cause
    # reloads from setting off infinite loops

        buttons = []
        iter    = current_scan_options.each_backend_option()
        for         i in iter :
            ( name, val ) =           current_scan_options.get_backend_option_by_index(i)
            opt = options.by_name(name)
            if "type"  in opt and opt["type"] == "TYPE_BUTTON" :
                buttons.append(name)  


        for  button in         buttons :
            current_scan_options.remove_backend_option_by_name(button)


    # Reapply current options to ensure the same values are still set.

        self.add_current_scan_options(current_scan_options)

    # In case the geometry values have changed,
    # update the available paper formats

        self.set_paper_formats( self.paper_formats )
        return


    def _update_option( self, opt, new_opt ) :
    

    # could be undefined for !($new_opt->{cap} & SANE_CAP_SOFT_DETECT)
    # or where $opt->{name} is not defined
    # e.g. $opt->{type} == SANE_TYPE_GROUP

        if opt["type"] == "TYPE_GROUP"        or "name" not   in opt        or   opt["name"]   not   in self.option_widgets     :
            return

        widget = self.option_widgets[ opt["name"] ]
        if new_opt["name"] != opt["name"] :
            logger.error(
            'Error updating options: reloaded options are numbered differently'
        )
            return True

        if opt["type"] != new_opt["type"] :
            logger.error(
            'Error updating options: reloaded options have different types')
            return True


    # Block the signal handler for the widget to prevent infinite
    # loops of the widget updating the option, updating the widget, etc.

        widget.signal_handler_block( widget["signal"] )
        opt = new_opt
        value = opt["val"]

    # HBox for option

        hbox = widget.get_parent()
        hbox.set_sensitive(
        ( not opt["cap"] & "CAP_INACTIVE" )           and opt["cap"] & "CAP_SOFT_SELECT" )
        if opt["max_values"] < 2 :

        # Switch

            if opt["type"] == "TYPE_BOOL" :
                if self.value_for_active_option( value, opt ) :
                    widget.set_active(value)

 
            else :
                if  opt["constraint_type"] =="CONSTRAINT_RANGE":
                    ( step, page ) = widget.get_increments()
                    step = 1
                    if opt["constraint"]["quant"] :
                        step = opt["constraint"]["quant"]

                    widget.set_range( opt["constraint"]["min"],
                        opt["constraint"]["max"] )
                    widget.set_increments( step, page )
                    if self.value_for_active_option( value, opt ) :
                        widget.set_value(value)


                elif  opt["constraint_type"] in [
                "CONSTRAINT_STRING_LIST", "CONSTRAINT_WORD_LIST" ]:
                    widget.get_model().clear()
                    index = 0
                    for _ in                      range(len( opt["constraint"] )-1+1)    :
                        widget.append_text(
                            d_sane.get( opt["constraint"][_] ) )
                        if  (value is not None)                            and opt["constraint"][_] == value                         :
                            index = _


                    if  (index is not None) :
                        widget.set_active(index)

                elif  opt["constraint_type"] =="CONSTRAINT_NONE":
                    if self.value_for_active_option( value, opt ) :
                        widget.set_text(value)




        widget.signal_handler_unblock( widget["signal"] )
        return



    def set_paper_formats( self, formats ) :
        """Add paper size to combobox if scanner large enough
"""    
        combobp = self.combobp
        if  (combobp is not None) :

        # Remove all formats, leaving Manual and Edit

            n = combobp.get_num_rows()
            while n>2 :
                n-=1
                combobp.remove(0)
            self.ignored_paper_formats = ()
            options = self.available_scan_options
            for _ in              formats.keys()   :
                if options.supports_paper( formats[_], PAPER_TOLERANCE )             :
                    logger.debug(f"Options support paper size '{_}'.")
                    combobp.prepend_text(_)
 
                else :
                    logger.debug(f"Options do not support paper size '{_}'.")
                    self.ignored_paper_formats.append(_)  



        # Set the combobox back from Edit to the previous value

            paper = self.paper
            if   (paper is None) :
                paper = _('Manual')
            combobp.set_active_by_text(paper)

        return


    def set_paper( self, paper ) :
        """Treat a paper size as a profile, so build up the required profile of geometry
settings and apply it
"""    
        if   (paper is None) :
            self.paper = paper
            self.current_scan_options.remove_frontend_option('paper')
            self.emit( 'changed-paper', paper )
            return

        for _ in          self.ignored_paper_formats  :
            if _ == paper :
                if  (logger is not None) :
                    logger.info(f"Ignoring unsupported paper {paper}")

                return


        formats       = self.paper_formats
        options       = self.available_scan_options
        paper_profile = Profile()
        if (options.by_name("page-height") is not None)        and not options.by_name("page-height")["cap"] &        "CAP_INACTIVE"        and (options.by_name("page-width") is not None)        and not options.by_name("page-width")["cap"] &        "CAP_INACTIVE"     :
            paper_profile.add_backend_option( "page-height",
            formats[paper]["y"] + formats[paper]["t"],
            options.by_name("page-height")["val"]
        )
            paper_profile.add_backend_option( "page-width",
            formats[paper]["x"] + formats[paper]["l"],
            options.by_name("page-width")["val"]
        )

        paper_profile.add_backend_option( "tl-x",
        formats[paper]["l"],
        options.by_name("tl-x")["val"]
    )
        paper_profile.add_backend_option( "tl-y",
        formats[paper]["t"],
        options.by_name("tl-y")["val"]
    )
        paper_profile.add_backend_option( "br-x",
        formats[paper]["x"] + formats[paper]["l"],
        options.by_name("br-x")["val"]
    )
        paper_profile.add_backend_option( "br-y",
        formats[paper]["y"] + formats[paper]["t"],
        options.by_name("br-y")["val"]
    )

    # forget the previous option info calls, as these are only interesting
    # *whilst* setting a profile, and now we are starting from scratch

        del(self.option_info) 
        if not paper_profile.num_backend_options() :
            self.hide_geometry(options)
            self.paper = paper
            self.current_scan_options.add_frontend_option( 'paper', paper )
            self.emit( 'changed-paper', paper )
            return

        signal=None
        def anonymous_27( dialog, profile, uuid ):
            
            if paper_profile["uuid"] == uuid :
                self.disconnect(signal)
                self.hide_geometry(options)
                self.paper = paper
                self.current_scan_options                   .add_frontend_option( 'paper', paper )
                self.emit( 'changed-paper', paper )



        signal = self.connect(
        'changed-current-scan-options' , anonymous_27 
    )

    # Don't trigger the changed-paper signal
    # until we have finished setting the profile

        self.add_current_scan_options(paper_profile)
        return


    def edit_paper(self) :
        """Paper editor
"""    
        combobp = self.combobp
        options = self.available_scan_options
        formats = self.paper_formats
        window = Dialog(
        transient_for = self,
        title           = _('Edit paper size'),
    )
        vbox = window.get_content_area()

    # Buttons for SimpleList

        hboxl = Gtk.HBox()
        vbox.pack_start( hboxl, False, False, 0 )
        vboxb = Gtk.VBox()
        hboxl.pack_start( vboxb, False, False, 0 )
        dbutton = Gtk.Button.new_from_stock('gtk-add')
        vboxb.pack_start( dbutton, True, False, 0 )
        rbutton = Gtk.Button.new_from_stock('gtk-remove')
        vboxb.pack_end( rbutton, True, False, 0 )

    # Set up a SimpleList

        slist = Gtk.SimpleList({
        _('Name')   : 'text',
        _('Width')  : 'int',
        _('Height') : 'int',
        _('Left')   : 'int',
        _('Top')    : 'int',
        _('Units')  : 'text',
    })
        for _ in          formats.keys()   :
            slist["data"].append([
            _,                formats[_]["x"], formats[_]["y"],             formats[_]["l"], formats[_]["t"], 'mm',
          ])            


    # Set everything to be editable except the units

        columns = slist.get_columns()
        for _ in          range(len(columns)-1-1+1)      :
            slist.set_column_editable( _, True )

        slist.get_column(0).set_sort_column_id(0)

        def anonymous_28():
            """    # Add button callback
"""
            rows = slist.get_selected_indices()
            if not rows :
                rows[0] = 0
            name    = slist["data"][ rows[0] ][0]
            version = 2
            i       = 0
            while i < len( slist["data"] ) :
                if slist["data"][i][0] == f"{name} ({version})" :
                    version+=1
                    i = 0
 
                else :
                    i+=1


            line = [f"{name} ({version})"]
            columns = slist.get_columns()
            for _ in              range(1,len(columns)-1+1)    :
                line.append(slist["data"][ rows[0] ][_])  

            del(slist["data"][rows[0]+1])      
            slist["data"].insert(rows[0]+1,line)


        dbutton.connect(
        'clicked' , anonymous_28 
    )

        def anonymous_29():
            """    # Remove button callback
"""
            rows = slist.get_selected_indices()
            if len(rows)-1 == len( slist["data"] )-1 :
                main.show_message_dialog(
                    parent  = window,
                    type    = 'error',
                    buttons = 'close',
                    text    = _('Cannot delete all paper sizes')
                )
 
            else :
                while rows :
                    del(slist["data"][(rows).pop(0)])   




        rbutton.connect(
        'clicked' , anonymous_29 
    )

        def anonymous_30( model, path, iter ):
            """    # Set-up the callback to check that no two Names are the same
"""            
            for _ in              range(len( slist["data"] )-1+1)    :
                if _ != path.to_string()                    and slist["data"][ path.to_string() ][0] ==                    slist["data"][_][0]                 :
                    name    = slist["data"][ path.to_string() ][0]
                    version = 2
                    regex=re.search(r"""
                     (.*) # name
                     [ ][(] # space, opening bracket
                     (\d+) # version
                     [)] # closing bracket
                   """,name,re.MULTILINE|re.DOTALL|re.VERBOSE)
                    if   regex                     :
                        name    = regex.group(1)
                        version = regex.group(2) + 1

                    slist["data"][ path.to_string() ][0] =                       f"{name} ({version})"
                    return




        slist.get_model().connect(
        'row-changed' , anonymous_30 
    )
        hboxl.pack_end( slist, False, False, 0 )

    # Buttons

        hboxb = Gtk.HBox()
        vbox.pack_start( hboxb, False, False, 0 )
        abutton = Gtk.Button.new_from_stock('gtk-apply')
        def anonymous_31():
            formats={}
            for  i in              range(len( slist["data"] )-1+1)    :
                j = 0
                for _ in                 ["x","y","l","t"] :
                    j+=1
                    formats[ slist["data"][i][0] ][_] =                       slist["data"][i][ j ]



            # Add new definitions

            self.paper_formats=formats
            if self.ignored_paper_formats                and len( self.ignored_paper_formats )             :
                main.show_message_dialog(
                    parent  = window,
                    type    = 'warning',
                    buttons = 'close',
                    text    = _(
'The following paper sizes are too big to be scanned by the selected device:'
                      )
                      + " "
                      + ', '.join( self.ignored_paper_formats )
                )

            window.destroy()


        abutton.connect(
        'clicked' , anonymous_31 
    )
        hboxb.pack_start( abutton, True, False, 0 )
        cbutton = Gtk.Button.new_from_stock('gtk-cancel')
        def anonymous_32():

            # Set the combobox back from Edit to the previous value

            combobp.set_active_by_text( self.paper )
            window.destroy()


        cbutton.connect(
        'clicked' , anonymous_32 
    )
        hboxb.pack_end( cbutton, True, False, 0 )
        window.show_all()
        return


    def save_current_profile( self, name ) :
        """keeping this as a separate sub allows us to test it
"""    
        self.add_profile( name, self.current_scan_options )

    # Block signal or else we fire another round of profile loads

        self.combobsp.signal_handler_block( self.combobsp_changed_signal )
        self.combobsp.set_active( self.combobsp.get_num_rows() - 1 )
        self.combobsp       .signal_handler_unblock( self.combobsp_changed_signal )
        self.profile = name
        return


    def add_profile( self, name, profile ) :
    
        if   (name is None) :
            logger.error('Cannot add profile with no name')
            return
 
        elif   (profile is None) :
            logger.error('Cannot add undefined profile')
            return
 
        elif type(profile) != 'Gscan2pdf::Scanner::Profile' :
            logger.error(
            type(profile) + ' is not a Gscan2pdf::Scanner::Profile object' )
            return


    # if we don't clone the profile,
    # we get strange action-at-a-distance problems

        self.profiles[name] = deepcopy(profile)
        self.combobsp.remove_item_by_text(name)
        self.combobsp.append_text(name)
        logger.debug( f"Saved profile '{name}':",
        Dumper( self.profiles[name].get_data() ) )
        self.emit( 'added-profile', name, self.profiles[name] )
        return


    def set_profile( self, name ) :
    
        if  (name is not None) and name != "" :

        # Only emit the changed-profile signal when the GUI has caught up

            signal=None
            def anonymous_33( _1, _2, uuid_found ):
                
                uuid = self.setting_profile[0]

                # there seems to be a race condition in t/0621_Dialog_Scan_CLI.t
                # where the uuid set below is not set in time to be tested in
                # this if.

                if uuid == uuid_found :
                    self.disconnect(signal)
                    self.setting_profile = []

                    # set property before emitting signal to ensure callbacks
                    # receive correct value

                    self.profile = name
                    self.emit( 'changed-profile', name )



            signal = self.connect(            'changed-current-scan-options' , anonymous_33         )

        # Add UUID to the stack and therefore don't unset the profile name

            self.setting_profile.append(self.profiles[name]["uuid"])  
            self.set_current_scan_options( self.profiles[name] )
      # no need to wait - nothing to do

        else :
        # set property before emitting signal to ensure callbacks
        # receive correct value

            self.profile = name
            self.emit( 'changed-profile', name )

        return



    def remove_profile( self, name ) :
        """Remove the profile. If it is active, deselect it first.
"""    
        if  (name is not None) and  name  in self.profiles :
            self.combobsp.remove_item_by_text(name)
            self.emit( 'removed-profile', name )
            del(self.profiles[name]) 

        return






    def value_for_active_option( self, value, opt ) :
    
        return (  (value is not None) and not opt["cap"] & "CAP_INACTIVE" )



    def set_options( self, opt ) :
        """display Goo::Canvas with graph
"""    

    # Set up the canvas

        window = Dialog(
        transient_for = self,
        title           = d_sane.get( opt["title"] ),
    )
        canvas = GooCanvas2.Canvas()
        canvas.set_size_request( CANVAS_SIZE, CANVAS_SIZE )
        canvas["border"] = CANVAS_BORDER
        window.get_content_area().add(canvas)
        root = canvas.get_root_item()
        def anonymous_34( widget, event ):
            
            if  "selected"  in widget :
                widget["selected"].fill_color='black'
                widget["selected"]=None

            if ( len( widget["val"] )-1 + 1 >= opt["max_values"]                or widget["on_val"] ):
                return False                
            fleur = Gdk.Cursor('fleur')
            ( x, y ) = to_graph( widget, event.x(), event.y() )
            x = int(x) + 1
            if x > len( widget["val"] ) :
                widget["val"].append(y)  
                widget["items"].append(add_value( root, widget ))  
 
            else :
                del(widget["val"][x])    
                widget["val"].insert(x,y)
                del(widget["items"][x])                      
                widget["items"].insert(x,add_value( root, widget ))

            update_graph(widget)
            return True


        canvas.connect(
        'button-press-event' , anonymous_34 
    )
        def anonymous_35( widget, event ):
            
            if event.keyval == Gdk.KEY_Delete                and  "selected"  in widget             :
                item = widget["selected"]
                widget["selected"]=None
                widget["on_val"] = False
                del(widget["val"][item["index"]])     
                del(widget["items"][item["index"]])   
                parent = item.get_parent()
                num    = parent.find_child(item)
                parent.remove_child(num)
                update_graph(widget)

            return False


        canvas.connect_after(
        'key-press-event',
        anonymous_35 
    )
        canvas.grab_focus(root)
        canvas["opt"] = opt
        canvas["val"] = canvas["opt"]["val"]
        for _ in          canvas["val"]  :
            canvas["items"].append(add_value( root, canvas ))  

        if opt["constraint_type"] == "CONSTRAINT_WORD_LIST" :
            opt["constraint"] =           sorted(opt["constraint"])  

        def anonymous_36():
            self.set_option( opt, canvas["val"] )

 # when INFO_INEXACT is implemented, so that the value is reloaded, check for it
 # here, so that the reloaded value is not overwritten.

            opt["val"] = canvas["val"]
            window.destroy()


        def anonymous_37():
            window.destroy()

        window.add_actions(
        gtk_apply = anonymous_36 ,
        gtk_cancel = anonymous_37 
    )

# Have to show the window before updating it otherwise is doesn't know how big it is

        window.show_all()
        update_graph(canvas)
        return





    def set_current_scan_options( self, profile ) :
        """convert from graph co-ordinates to canvas co-ordinates



convert from canvas co-ordinates to graph co-ordinates





Set options to profile referenced by hashref
"""    
        if   (profile is None) :
            logger.error('Cannot add undefined profile')
            return
 
        elif type(profile) != 'Gscan2pdf::Scanner::Profile' :
            logger.error(
            type(profile) + ' is not a Gscan2pdf::Scanner::Profile object' )
            return


    # forget the previous option info calls, as these are only interesting
    # *whilst* setting a profile, and now we are starting from scratch

        del(self.option_info) 

    # If we have no options set, no need to reset to defaults

        if self.current_scan_options.num_backend_options() == 0 :
            self.add_current_scan_options(profile)
            return


    # reload to get defaults before applying profile

        signal=None
        self.current_scan_options =       Profile.new_from_data( deepcopy(profile) )
        def anonymous_43():
            self.disconnect(signal)
            self.add_current_scan_options(profile)


        signal = self.connect(
        'reloaded-scan-options' , anonymous_43 
    )
        self.scan_options( self.device )
        return



    def add_current_scan_options( self, profile ) :
        """Apply options referenced by hashref without resetting existing options
"""    
        if   (profile is None) :
            logger.error('Cannot add undefined profile')
            return
 
        elif type(profile) != 'Gscan2pdf::Scanner::Profile' :
            logger.error(
            type(profile) + ' is not a Gscan2pdf::Scanner::Profile object' )
            return


    # First clone the profile, as otherwise it would be self-modifying

        clone = deepcopy(profile)
        self.setting_current_scan_options.append(clone["uuid"])  

    # Give the GUI a chance to catch up between settings,
    # in case they have to be reloaded.
    # Use the callback to trigger the next loop

        self._set_option_profile( clone, clone.each_backend_option() )
        return


    def _set_option_profile( self, profile, next, step ) :
    
        self.cursor='wait'
        if         i in next(step) :
            ( name, val ) = profile.get_backend_option_by_index(i)
            options = self.available_scan_options
            opt     = options.by_name(name)
            if   (opt is None) or opt["cap"] & "CAP_INACTIVE" :
                logger.warn(f"Ignoring inactive option '{name}'.")
                self._set_option_profile( profile, next )
                return


        # Don't try to set invalid option

            if opt["constraint"] and isinstance( opt["constraint"] ,list)   :
                index = opt["constraint"].index( val )  
                if index == NO_INDEX :
                    logger.warn(
                    f"Ignoring invalid argument '{val}' for option '{name}'.")
                    self._set_option_profile( profile, next )
                    return



   # Ignore option if info from previous set_option() reported SANE_INFO_INEXACT

            if    opt["name"]    in self.option_info            and self.option_info[ opt["name"] ] & "INFO_INEXACT"         :
                logger.warn(
f"Skip setting option '{name}' to '{val}', as previous call set SANE_INFO_INEXACT"
            )
                self._set_option_profile( profile, next )
                return


        # Ignore option if value already within tolerance

            if Options.within_tolerance(
                opt, val, OPTION_TOLERANCE
            )         :
                logger.info(
                f"No need to set option '{name}': already within tolerance.")
                self._set_option_profile( profile, next )
                return

            logger.debug(
            f"Setting option '{name}'"
              + (
                    
                "" if opt["type"]=="TYPE_BUTTON" 
                else f" from '{opt}->{val}' to '{val}'."
              )
        )
            signal=None
            def anonymous_44( widget, optname, optval, uuid ):
                

                # With multiple reloads, this can get called several times,
                # so only react to signal from the correct profile

                if  (uuid is not None) and uuid == profile["uuid"] :
                    self.disconnect(signal)
                    self._set_option_profile( profile, next )



            signal = self.connect(
            'changed-scan-option' , anonymous_44 
        )
            self.set_option( opt, val, profile["uuid"] )
 
        else :

        # Having set all backend options, set the frontend options
        # Set paper formats first to make sure that any paper required is
        # available

            self.set_paper_formats( self.paper_formats )
            iter = profile.each_frontend_option()
            for             key in iter :
                self.set( key, profile.get_frontend_option(key) )

            if not len( self.setting_profile ) :
                self.profile=None

            pop(self.setting_current_scan_options)
            self.emit(
            'changed-current-scan-options',
            self.current_scan_options,
            profile["uuid"]
        )
            self.cursor='default'

        return


    def update_widget_value( self, opt, val ) :
    
        widget = self.option_widgets[ opt["name"] ]
        if  (widget is not None) :
            logger.debug( f"Setting widget '{opt}->{name}'"
              + (    "" if opt["type"]=="TYPE_BUTTON"  else f" to '{val}'." ) )
            widget.signal_handler_block( widget["signal"] )
            if issubclass(widget,CheckButton)                  or issubclass(widget,Switch):
                if val == "" :
                    val = 0
                if widget.get_active() != val :
                    widget.set_active(val)


            elif issubclass(widget,SpinButton):
                if widget.get_value() != val :
                    widget.set_value(val)


            elif issubclass(widget,ComboBox):
                if opt["constraint"][ widget.get_active() ] != val :
                    index =                       opt["constraint"].index( val )  
                    if index > NO_INDEX :
                        widget.set_active(index)


            elif issubclass(widget,Entry):
                if widget.get_text() != val :
                    widget.set_text(val)


            widget.signal_handler_unblock( widget["signal"] )
 
        else :
            logger.warn(f"Widget for option '{opt}->{name}' undefined.")

        return




    def get_xy_resolution(self) :
    
        options = self.available_scan_options
        if   (options is None) :
            return
        resolution = options.by_name("resolution")
        x          = options.by_name('x-resolution')
        y          = options.by_name('y-resolution')
        if  (resolution is not None) :
            resolution = resolution["val"]
        if  (x is not None)          :
            x          = x["val"]
        if  (y is not None)          :
            y          = y["val"]

    # Potentially, a scanner could offer all three options, but then unset
    # resolution once the other two have been set.

        if  (resolution is not None) :

        # The resolution option, plus one of the other two, is defined.
        # Most sensibly, we should look at the order they were set.
        # However, if none of them are in current-scan-options, they still have
        # their default setting, and which of those gets priority is certainly
        # scanner specific.

            if  (x is not None) or  (y is not None) :
                current_scan_options = self.current_scan_options
                iter = current_scan_options.each_backend_option()
                for                 i in iter :
                    ( name, val ) =                   current_scan_options.get_backend_option_by_index(i)
                    if name == "resolution" :
                        x = val
                        y = val
 
                    elif name == 'x-resolution' :
                        x = val
 
                    elif name == 'y-resolution' :
                        y = val


 
            else :
                return resolution, resolution


        if   (x is None) :
            x = Document.POINTS_PER_INCH
        if   (y is None) :
            y = Document.POINTS_PER_INCH
        return x, y



    def update_num_pages(self) :
        """Update the number of pages to scan spinbutton if necessary
"""    
        slist = self.document
        if   (slist is None) :
            return
        n = slist.pages_possible( self.page_number_start,
        self.page_number_increment )
        if n > 0 and n < self.num_pages :
            self.num_pages=n

        return



    def update_start_page(self) :
        """Called either from changed-value signal of spinbutton,
or row-changed signal of simplelist
"""    
        slist = self.document
        if   (slist is None) :
            return
        value = self.page_number_start
        if   (start is None) :
            start = self.page_number_start
        step = value - start
        if step == 0 :
            step = self.page_number_increment
        start = value
        while slist.pages_possible( value, step ) == 0 :
            if value < 1 :
                value = 1
                step  = 1
 
            else :
                value += step


        self.page_number_start=value
        start = value
        self.update_num_pages()
        return



    def reset_start_page(self) :
        """Reset start page number after delete or new
"""    
        slist = self.document
        if   (slist is None) :
            return
        if len( slist["data"] )-1 > NO_INDEX :
            start_page = self.page_number_start
            step       = self.page_number_increment
            if start_page > slist["data"][ len( slist["data"] )-1 ][0] + step :
                self.page_number_start=slist

 
        else :
            self.page_number_start=1

        return


    def set_cursor( self, cursor ) :
    
        win = self.get_window()
        if   (cursor is None) :
            cursor = self.cursor

        if  (win is not None) :
            display = Gdk.Display.get_default
            win.set_cursor(
            Gdk.Cursor.new_from_name( display, cursor ) )

        self.scan_button.set_sensitive( cursor == 'default' )
        return


    def get_label_for_option( self, name ) :
    
        widget = self.option_widgets[name]
        hbox   = widget.get_parent()
        for  child in          hbox.get_children()  :
            if issubclass(child,Label) :
                return child.get_text()


        return





def _save_profile_callback( widget, parent ) :
    
    dialog = Gtk.Dialog(
        _('Name of scan profile'), parent,
        'destroy-with-parent',
        gtk_save   = 'ok',
        gtk_cancel = 'cancel'
    )
    hbox  = Gtk.HBox()
    label = Gtk.Label( label=_('Name of scan profile') )
    hbox.pack_start( label, False, False, 0 )
    entry = Gtk.Entry()
    entry.set_activates_default(True)
    hbox.pack_end( entry, True, True, 0 )
    dialog.get_content_area().add(hbox)
    dialog.set_default_response('ok')
    dialog.show_all()
    flag = True
    while flag :
        if dialog.run() == 'ok' :
            name = entry.get_text()
            if   notre.search(r"^\s*$",name,re.MULTILINE|re.DOTALL|re.VERBOSE) :
                if  name  in parent["profiles"] :
                    warning = _("Profile '%s' exists. Overwrite?") % (name)                                              
                    dialog2 = Gtk.Dialog(
                        warning, dialog, 'destroy-with-parent',
                        gtk_ok     = 'ok',
                        gtk_cancel = 'cancel'
                    )
                    label = Gtk.Label(label=warning)
                    dialog2.get_content_area().add(label)
                    label.show()
                    if dialog2.run() == 'ok' :
                        parent.save_current_profile( entry.get_text() )
                        flag = False

                    dialog2.destroy()
 
                else :
                    parent.save_current_profile( entry.get_text() )
                    flag = False


 
        else :
            flag = False


    dialog.destroy()
    return

def _edit_profile_callback( widget, parent ) :
    
    name = parent.profile
    ( msg, profile )=(None,None)
    if   (name is None) or name == "" :
        msg     = _('Editing current scan options')
        profile = parent["current_scan_options"]
 
    else :
        msg     = _('Editing scan profile "%s"') % (name)  
        profile = parent["profiles"][name]

    dialog = Gtk.Dialog(
        msg, parent,
        'destroy-with-parent',
        gtk_ok     = 'ok',
        gtk_cancel = 'cancel'
    )
    label = Gtk.Label(label=msg)
    dialog.get_content_area().pack_start( label, True, True, 0 )

    # Clone so that we can cancel the changes, if necessary

    profile = deepcopy(profile)
    _build_profile_table( profile, parent.available_scan_options,
        dialog.get_content_area() )
    dialog.set_default_response('ok')
    dialog.show_all()

    # save the profile and reload

    if dialog.run() == 'ok' :
        if   (name is None) or name == "" :
            parent.set_current_scan_options(profile)
 
        else :
            parent["profiles"][name] = profile

            # unset profile to allow us to set it again on reload

            parent["profile"] = None

            # emit signal to update settings

            parent.emit( 'added-profile', name,
                parent["profiles"][name] )
            signal=None
            def anonymous_19():
                parent.disconnect(signal)
                parent.set_profile(name)


            signal = parent.connect(
                'reloaded-scan-options' , anonymous_19 
            )
            parent.scan_options( parent.device )


    dialog.destroy()
    return

def _build_profile_table( profile, options, vbox ) :
    
    frameb = Gtk.Frame( label=_('Backend options') )
    framef = Gtk.Frame( label=_('Frontend options') )
    vbox.pack_start( frameb, True, True, 0 )
    vbox.pack_start( framef, True, True, 0 )

    # listbox to align widgets

    listbox = Gtk.ListBox()
    listbox.set_selection_mode('none')
    frameb.add(listbox)
    iter = profile.each_backend_option()
    for     i in iter :
        ( name, val ) = profile.get_backend_option_by_index(i)
        opt   = options.by_name(name)
        row   = Gtk.ListBoxRow()
        hbox  = Gtk.HBox()
        label = Gtk.Label( label=d_sane.get( opt["title"] ) )
        hbox.pack_start( label, False, True, 0 )
        button = Gtk.Button.new_from_stock('gtk-delete')
        hbox.pack_end( button, False, False, 0 )
        def anonymous_20():
            logger.debug(f"removing option '{name}' from profile")
            profile.remove_backend_option_by_index(i)
            frameb.destroy()
            framef.destroy()
            _build_profile_table( profile, options, vbox )


        button.connect(
            'clicked' , anonymous_20 
        )
        row.add(hbox)
        listbox.add(row)

    listbox = Gtk.ListBox()
    listbox.set_selection_mode('none')
    framef.add(listbox)
    iter = profile.each_frontend_option()
    for     name in iter :
        row   = Gtk.ListBoxRow()
        hbox  = Gtk.HBox()
        label = Gtk.Label(label=name)
        hbox.pack_start( label, False, True, 0 )
        button = Gtk.Button.new_from_stock('gtk-delete')
        hbox.pack_end( button, False, False, 0 )
        def anonymous_21():
            logger.debug(f"removing option '{name}' from profile")
            profile.remove_frontend_option(name)
            frameb.destroy()
            framef.destroy()
            _build_profile_table( profile, options, vbox )


        button.connect(
            'clicked' , anonymous_21 
        )
        row.add(hbox)
        listbox.add(row)

    vbox.show_all()
    return

def _new_val( oldval, newval ) :
    
    return (
    (  (newval is not None) and  (oldval is not None) and newval != oldval )           or (  (newval is not None) ^  (oldval is not None) )
    )

def _extended_pagenumber_checkbox_callback( widget, param, data ) :
    
    ( dialog, spin_buttoni ) = len(data)
    if widget.get_active() :
        dialog["frames"].hide()
        dialog["framex"].show_all()
 
    else :
        if spin_buttoni.get_value() == 1 :
            dialog["buttons"].set_active(True)
 
        elif spin_buttoni.get_value() > 0 :
            dialog["buttond"].set_active(True)
            dialog["combobs"].set_active(False)
 
        else :
            dialog["buttond"].set_active(True)
            dialog["combobs"].set_active(True)

        dialog["frames"].show_all()
        dialog["framex"].hide()

    return

def multiple_values_button_callback( widget, data ) :
    
    ( dialog, opt )  = len(data)
    if opt["type"] == "TYPE_FIXED"        or opt["type"] == "TYPE_INT"     :
        if opt["constraint_type"] == "CONSTRAINT_NONE" :
            main.show_message_dialog(
                parent  = dialog,
                type    = 'info',
                buttons = 'close',
                text    = _(
'Multiple unconstrained values are not currently supported. Please file a bug.'
                )
            )
 
        else :
            dialog.set_options(opt)

 
    else :
        main.show_message_dialog(
            parent  = dialog,
            type    = 'info',
            buttons = 'close',
            text    = _(
'Multiple non-numerical values are not currently supported. Please file a bug.'
            )
        )

    return

def add_value( root, canvas ) :
    
    item = GooCanvas2.CanvasRect(
        parent       = root,
        x            = 0,
        y            = 0,
        width        = CANVAS_POINT_SIZE,
        height       = CANVAS_POINT_SIZE,
        fill_color = 'black',
        line_width = 0,
    )
    def anonymous_38():
        canvas["on_val"] = True
        return True


    item.connect(
        'enter-notify-event' , anonymous_38 
    )
    def anonymous_39():
        canvas["on_val"] = False
        return True


    item.connect(
        'leave-notify-event' , anonymous_39 
    )
    def anonymous_40( widget, target, ev ):
            
        canvas["selected"] = item
        item.fill_color='red'
        fleur = Gdk.Cursor('fleur')
        widget.get_canvas().pointer_grab( widget,
                [
        'pointer-motion-mask', 'button-release-mask' ],
                fleur, ev.time() )
        return True


    item.connect(
        'button-press-event' , anonymous_40 
    )
    def anonymous_41( widget, target, ev ):
            
        widget.get_canvas().pointer_ungrab( widget, ev.time() )
        return True


    item.connect(
        'button-release-event' , anonymous_41 
    )
    opt = canvas["opt"]
    def anonymous_42( widget, target, event ):
            
        if not(
                    event.state() >=  ## no critic (ProhibitMismatchedOperators)
                    'button1-mask'
                )             :
            return False

        ( x, y ) = ( event.x(), event.y() )
        ( xgr, ygr ) = ( 0, y )
        if opt["constraint_type"] == "CONSTRAINT_RANGE" :
            ( xgr, ygr ) = to_graph( canvas, 0, y )
            if ygr > opt["constraint"]["max"] :
                ygr = opt["constraint"]["max"]
 
            elif ygr < opt["constraint"]["min"] :
                ygr = opt["constraint"]["min"]

 
        elif opt["constraint_type"] == "CONSTRAINT_WORD_LIST" :
            ( xgr, ygr ) = to_graph( canvas, 0, y )
            for _ in              range(1,len( opt["constraint"] )-1+1)    :
                if ygr < (
                            opt["constraint"][_] +
                              opt["constraint"][ _ - 1 ]
                        ) / 2                     :
                    ygr = opt["constraint"][ _ - 1 ]
                    break
 
                elif _ == len( opt["constraint"] )-1 :
                    ygr = opt["constraint"][_]



        canvas["val"][ widget["index"] ] = ygr
        ( x, y ) = to_canvas( canvas, xgr, ygr )
        widget.set( y = y - CANVAS_POINT_SIZE / 2 )
        return True


    item.connect(
        'motion-notify-event' , anonymous_42 
    )
    return item

def to_canvas( canvas, x, y ) :
    
    return ( x - canvas["bounds"][0] ) * canvas["scale"][0] +       canvas["border"],       canvas["cheight"] -       ( y - canvas["bounds"][1] ) * canvas["scale"][1] -       canvas["border"]

def to_graph( canvas, x, y ) :
    
    return ( x - canvas["border"] ) / canvas["scale"][0] +       canvas["bounds"][0],       ( canvas["cheight"] - y - canvas["border"] ) / canvas["scale"][1] +       canvas["bounds"][1]

def update_graph(canvas) :
    

    # Calculate bounds of graph

    ( xbounds, ybounds )=([],[])
    for _ in      canvas["val"]  :
        if   (ybounds[0] is None) or _ < ybounds[0] :
            ybounds[0] = _

        if   (ybounds[1] is None) or _ > ybounds[1] :
            ybounds[1] = _


    opt = canvas["opt"]
    xbounds[0] = 0
    xbounds[1] = len( canvas["val"] )-1
    if xbounds[0] >= xbounds[1] :
        xbounds[0] = -CANVAS_MIN_WIDTH / 2
        xbounds[1] = CANVAS_MIN_WIDTH / 2

    if opt["constraint_type"] == "CONSTRAINT_RANGE" :
        ybounds[0] = opt["constraint"]["min"]
        ybounds[1] = opt["constraint"]["max"]
 
    elif opt["constraint_type"] == "CONSTRAINT_WORD_LIST" :
        ybounds[0] = opt["constraint"][0]
        ybounds[1] = opt["constraint"][ len( opt["constraint"] )-1 ]

    ( vwidth, vheight ) =       ( xbounds[1] - xbounds[0], ybounds[1] - ybounds[0] )

    # Calculate bounds of canvas

    ( x, y, cwidth, cheight ) = canvas.get_bounds()

    # Calculate scale factors

    scale = [
    ( cwidth - canvas["border"] * 2 ) / vwidth,         ( cheight - canvas["border"] * 2 ) / vheight
    ]
    canvas["scale"] = scale
    canvas["bounds"] =       [
    xbounds[0], ybounds[0], xbounds[1], xbounds[1] ]
    canvas["cheight"] = cheight

    # Update canvas

    for _ in      range(len( canvas["items"] )-1+1)    :
        item = canvas["items"][_]
        item["index"] = _
        ( xc, yc ) = to_canvas( canvas, _, canvas["val"][_] )
        item.set(
            x = xc - CANVAS_BORDER / 2,
            y = yc - CANVAS_BORDER / 2
        )

    return

def make_progress_string( i, npages ) :
    
    if npages > 0:
        return _('Scanning page %d of %d') % (i, npages)
    return _('Scanning page %d') % (i)  
