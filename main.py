import gi
import os
from stat import S_ISDIR, S_ISREG
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Vte
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib
from gi.repository import GObject
from pathlib import Path
from paramiko import SSHClient
from scp import SCPClient
import time
import paramiko
import subprocess
import glob
from file_transfer import onRowCollapsed,onRowExpanded,populateFileSystemTreeStore,on_tree_selection_changed 
from ssh_file_transfer import onRowCollapsed2,onRowExpanded2,populateFileSystemTreeStore2,on_tree_selection_changed2,ssh_connect
from gi.repository.GdkPixbuf import Pixbuf


HOME = "HOME"
SHELLS = [ "/bin/bash" ]
DRAG_ACTION = Gdk.DragAction.COPY
ICONSIZE = Gtk.IconSize.MENU
get_icon = lambda name: Gtk.Image.new_from_icon_name(name, ICONSIZE)

TARGETS = [('MY_TREE_MODEL_ROW', Gtk.TargetFlags(2) , 0),
('text/plain', 0, 1),
('TEXT', 0, 2),('STRING', 0, 3),]




class MyWindow(Gtk.Window):

    notebook = Gtk.Notebook()
    home = str(Path.home())
    baglantilar = dict() # Goal 1
    __gsignals__ = {
        "close-tab": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_default_size(750, 500)
        self.connect("destroy", Gtk.main_quit)
        self.set_title("VALF")
        self.main()
        self.number_list = [1]
         
    def main(self):
        self.table = Gtk.Table(n_rows=10, n_columns=30, homogeneous=True)
        self.add(self.table)

        self.listbox = Gtk.ListBox()
        self.add(self.listbox)
        self.listbox_add_items()

        self.searchentry = Gtk.SearchEntry()
        self.searchentry.connect("activate",self.on_search_activated)
        self.add(self.searchentry)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_border_width(5)
        scrolled_window.set_policy(
            Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        
        scrolled_window.add_with_viewport(self.listbox)
        self.add(scrolled_window)

        new_window_button = Gtk.Button("Yeni Bağlantı")
        new_window_button.connect('clicked',self.add_newhost_window)
        self.toolbar()
        self.table.attach(self.box,0,10,0,1)
        self.table.attach(new_window_button,5,10,9,10)
        self.table.attach(scrolled_window,0,10,2,9)
        self.table.attach(self.searchentry,0,10,1,2)

        self.add(self.notebook)
        self.table.attach(self.notebook,10,30,0,10)

        self.notebook.show_all()
        self.listbox.show_all()
        self.searchentry.show_all()
        self.page1 = Gtk.Box()
        self.page1.set_border_width(10)
        self.page1.add(Gtk.Label(label = "İstediğiniz bağlantıya sol tıkladığınızda,\nbağlantı detaylarınız burada listelenecek."))
        self.notebook.append_page(self.page1, Gtk.Label("Ana Sayfa"))

    def ui_info(self):
        self.UI_INFO = """
    <ui>
    <menubar name='MenuBar'>
        <menu action='FileMenu'>
        <menuitem action='FileNew' />
        <menuitem action='FileNewNew' />
        </menu>
    </menubar>
    </ui>
    """      

    def toolbar(self):

        action_group = Gtk.ActionGroup(name="my_actions")
        uimanager = self.create_ui_manager()
        uimanager.insert_action_group(action_group)
        self.add_file_menu_actions(action_group)
        self.add_edit_menu_actions(action_group)
        menubar = uimanager.get_widget("/MenuBar")

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(menubar, False, False, 0)

        self.eventbox = Gtk.EventBox()
        self.box.pack_start(self.eventbox, True, True, 0)
    
    def add_edit_menu_actions(self, action_group):
        action_group.add_actions(
            [
                ("EditMenu", Gtk.STOCK_COPY, None, None, None, self.on_menu_others),
                ("EditCopy", Gtk.STOCK_COPY, None, None, None, self.on_menu_others),
                ("EditPaste", Gtk.STOCK_PASTE, None, None, None, self.on_menu_others),
                (
                    "EditSomething",
                    None,
                    "Something",
                    "<control><alt>S",
                    None,
                    self.on_menu_others,
                ),
            ]
        )
    
    def on_menu_others(self, widget):
        print("Menu item " + widget.get_name() + " was selected")
        
    def add_file_menu_actions(self, action_group):
        
        action_filemenu = Gtk.Action(name="FileMenu", label="Sertifikalar")
        action_group.add_action(action_filemenu)

        action_filenewmenu = Gtk.Action(name="FileNew", label = "Sertifikalarım")
        action_group.add_action(action_filenewmenu)
        action_filenewmenu.connect("activate", self.list_certificates)

        action_filenewnewmenu = Gtk.Action(name="FileNewNew", label = "Sertifika Oluştur")
        action_filenewnewmenu.connect("activate", self.cert_name_window)
        action_group.add_action(action_filenewnewmenu)
    
    def list_certificates(self,event):
        self.read_local_certificates()

        page = Gtk.ScrolledWindow()
        page.set_border_width(10)
        self.cert_listbox = Gtk.ListBox()
        self.notebook.remove_page(0)
        self.notebook.set_current_page(0)
        self.notebook.prepend_page(page, Gtk.Label("Ana Sayfa"))
        self.toolbar()
        
        for i in self.certificates:
            ## label yerine buton oluşturduk
            buttons = Gtk.Button.new_with_label(i)
            buttons.connect("button-press-event",self.button_clicked_cert)
            buttons.connect("button-press-event",self.on_cert_left_clicked)
            self.cert_listbox.add(buttons) 
        
        page.add_with_viewport(self.cert_listbox)
        self.cert_listbox.show_all()

        self.notebook.show_all()
    
    def context_menu_cert(self): # Buton sağ tıkında açılan menü 
        menu = Gtk.Menu()
        menu_item = Gtk.MenuItem("Delete Certificates")
        menu.append(menu_item)
        menu_item.connect("activate", self.delete_cert)
        menu.show_all()

        return menu

    ##  Buton sağ click ise context menu açtı
    def button_clicked_cert(self,listbox_widget,event): 
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            menu = self.context_menu_cert()
            ## Tıklanan objenin labelini print ediyor
            self.labelmenu_cert = listbox_widget.get_label()
            menu.popup( None, None, None,None, event.button, event.get_time()) 
            return True
    
    def delete_cert(self,action):
        cert_index = self.certificates.index(self.labelmenu_cert)
        self.cert_listbox.remove(self.cert_listbox.get_row_at_index(cert_index))
        self.cert_listbox.show_all()
        priv  = self.labelmenu_cert.rstrip('.pub')
        os.remove(self.labelmenu_cert)   
        os.remove(priv)    
       

    def on_cert_left_clicked(self,listbox_widget,event):
        desc = ""
        cert_path = listbox_widget.get_label().rstrip('\n')
        cert_name = os.path.basename(cert_path)

        with open(cert_path, 'r') as description:
            desc = description.read()
        dialog = Gtk.Dialog(transient_for=self, flags=0,title=cert_name)
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_size(750, 120)
        label = Gtk.Label(label=desc)
        label.set_line_wrap(True)
        label.set_selectable(True)
        scrollableWindow = Gtk.ScrolledWindow()
        scrollableWindow.add_with_viewport(label)
        scrollableWindow.set_min_content_width(750)
        scrollableWindow.set_min_content_height(100)
        content = dialog.get_content_area()
        content.add(scrollableWindow)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("WARN dialog closed by clicking OK button")

        dialog.destroy()        

    def read_local_certificates(self):
        self.certificates =  glob.glob(self.home+"/.ssh/*.pub")

    def create_ui_manager(self):
        uimanager = Gtk.UIManager()
        self.ui_info()
        uimanager.add_ui_from_string(self.UI_INFO)
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager

    def on_menu_file_quit(self, widget):
        Gtk.main_quit()
    
    def create_certificate(self,event):
        self.read_local_certificates()
        self.terminal3     = Vte.Terminal()
        self.terminal3.spawn_sync(
        Vte.PtyFlags.DEFAULT,
        os.environ[HOME],
        SHELLS,
        [],
        GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,)
        self.generate_ssh_cert = "ssh-keygen\n"
        self.cert_name = self.home + "/.ssh/" + self.cert_name_entry.get_text() + "\n"
        self.cert_name_none = "\n"
        self.passphrase = self.cert_pass_entry.get_text()+ "\n"

        self.terminal3.feed_child(self.generate_ssh_cert.encode("utf-8"))
        time.sleep(0.5)
        if self.cert_name_entry.get_text() == '':
            if 'id_rsa.pub\n' in self.certificates:
                self.cert_yes_no()
                time.sleep(0.5)
            else:
                self.terminal3.feed_child(self.cert_name_none.encode("utf-8"))
                time.sleep(0.5)
        else:
            self.terminal3.feed_child(self.cert_name.encode("utf-8"))
            time.sleep(0.5)

        self.terminal3.feed_child(self.passphrase.encode("utf-8"))
        time.sleep(0.5)
        self.terminal3.feed_child(self.passphrase.encode("utf-8"))
        time.sleep(0.5)
        self.list_certificates('clicked')
        self.cert_name_win.hide()

    
    def cert_yes_no(self):
        self.cert_yes_no_win = Gtk.Window()
        self.cert_yes_no_win.set_title("Are you sure ?")
        self.cert_yes_no_win.set_border_width(10)
        self.table13 = Gtk.Table(n_rows=2, n_columns=2, homogeneous=True)
        self.cert_yes_no_win.add(self.table13)

        self.cert_yes_no_label = Gtk.Label( label = "Zaten idrsa.pub isimli bir sertifikanız var. Oluşturacağınız yeni sertifika üzerine yazılacaktır.\n\t\t\t\t\t\t\t\t\tOnaylıyor musunuz ?")
        self.cert_yes_button = Gtk.Button("Yes")
        self.cert_no_button = Gtk.Button("No")

        self.cert_yes_button.connect('clicked',self.cert_yes)
        self.cert_no_button.connect('clicked',self.cert_no)

        self.cert_yes_no_win.add(self.cert_yes_button)
        self.cert_yes_no_win.add(self.cert_no_button)
        self.table13.attach(self.cert_yes_no_label,0,2,0,1)
        self.table13.attach(self.cert_yes_button,0,1,1,2)
        self.table13.attach(self.cert_no_button,1,2,1,2)

        self.cert_yes_no_win.present()
        self.cert_yes_no_win.show_all()
    
    def cert_yes(self,clicked):
        self.terminal3.feed_child(self.cert_name_none.encode("utf-8"))
        time.sleep(0.5)
        self.cert_yes_no_win.hide()
    
    def cert_no(self,clicked):
        self.cert_yes_no_win.hide()

    def send_certificate(self,event):
        self.terminal4     = Vte.Terminal()
        self.terminal4.spawn_sync(
        Vte.PtyFlags.DEFAULT,
        os.environ[HOME],
        SHELLS,
        [],
        GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,)

        self.send_cert = "ssh-copy-id -i" + self.cert_name + " " + self.baglantilar[self.get_host_before]['User']+"@" +self.baglantilar[self.get_host_before]['Hostname'] + "\n"
        self.terminal4.feed_child(self.send_cert.encode("utf-8"))
        time.sleep(0.5)

    def cert_name_window(self,event):
        self.cert_name_win = Gtk.Window()
        self.cert_name_win.set_title("Yeni Sertifika")

        self.cert_name_win.set_border_width(10)
        self.table11 = Gtk.Table(n_rows=3, n_columns=1, homogeneous=True)
        self.cert_name_win.add(self.table11)

        self.cert_name_entry = Gtk.Entry()
        self.cert_pass_entry = Gtk.Entry()
        self.cert_pass_entry.set_visibility(False)
        self.cert_name_button = Gtk.Button("Gönder")
        self.cert_name_button.connect("clicked",self.create_certificate)

        self.cert_name_entry.set_placeholder_text("Sertifika Adı (İsteğe Bağlı)")
        self.cert_pass_entry.set_placeholder_text("Sertifika Parolası (İsteğe Bağlı)")

        self.cert_name_win.add(self.cert_name_button)
        self.table11.attach(self.cert_name_entry,0,1,0,1)
        self.table11.attach(self.cert_pass_entry,0,1,1,2)
        self.table11.attach(self.cert_name_button,0,1,2,3)

        self.cert_name_win.present()
        self.cert_name_win.show_all()
    
    def connect_with_cert(self,event):
        self.terminal5     = Vte.Terminal()
        self.terminal5.spawn_sync(
        Vte.PtyFlags.DEFAULT,
        os.environ[HOME],
        SHELLS,
        [],
        GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,)
        
        self.connect_w_cert = "ssh " + self.get_host_before + "\n"
        
    def read_config(self): # Conf dosyasını gezer, değerleri okur, dictionary'e atar.
        try : 
            self.baglantilar.clear()
            with open(self.home+'/.ssh/config','r') as f:    
                for line in f: # Goal 2 
                    if 'Host ' in line: # Goal 3
                        if line != '\n':
                            
                            (key,value) = line.split()
                            hostline = value
                            self.baglantilar[hostline] = dict() # Goal 3
                            self.baglantilar[hostline][key] = value # Goal 5

                        else:
                            continue
                        
                    else: # Goal 4
                        if line != '\n':
                            (key,value) = line.split() 
                            self.baglantilar[hostline][key] = value
                    
                        else:
                            continue
        
        except:
            self.terminal     = Vte.Terminal()
            self.terminal.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            os.environ[HOME],
            SHELLS,
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,)
            self.create = "mkdir .ssh\n" + "cd .ssh\n"  + "touch config\n" + "touch known_hosts\n" + "touch authorized_keys\n"
            self.terminal.feed_child(self.create.encode("utf-8"))

    def write_config(self): # RAM'de tutulan dictionary değerlerini dosyaya yazar.
        with open(self.home+'/.ssh/config','w') as f:
            for p_id, p_info in self.baglantilar.items():
                for key in p_info:
                    f.write(key+" "+p_info[key]+"\n")

                
    def context_menu(self): # Buton sağ tıkında açılan menü 
        menu = Gtk.Menu()
        #menu_item = Gtk.MenuItem("Create New Notebook")
        #menu.append(menu_item)
        #menu_item.connect("activate", self.on_click_popup)

        menu_item_del = Gtk.MenuItem("Bağlantıyı Sil")
        menu.append(menu_item_del)
        menu_item_del.connect("activate",self.on_click_delete)

        menu_item_connect = Gtk.MenuItem("Bağlan")
        menu.append(menu_item_connect)
        menu_item_connect.connect("activate",self.on_click_connect)

        menu_item_scp = Gtk.MenuItem("Scp ile Dosya Gönder")
        menu.append(menu_item_scp)
        menu_item_scp.connect("activate",self.scp_transfer)

        menu.show_all()

        return menu

    ##  Buton sağ click ise context menu açtı
    def button_clicked(self,listbox_widget,event): 
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            menu = self.context_menu()
            ## Tıklanan objenin labelini print ediyor
            self.labelmenu = listbox_widget.get_label()
            menu.popup( None, None, None,None, event.button, event.get_time()) 
            return True               
                        
    def on_click_popup(self, action): ## Yeni sayfa oluştur
        self.new_page = Gtk.Box()
        self.new_page.set_border_width(10)

        self._button_box = Gtk.HBox()
        self._button_box.get_style_context().add_class("right")

        self.close_button()
        self.new_page.add(Gtk.Label(label=self.labelmenu))
        self.notebook.append_page(self.new_page, self._button_box)

        self.number = self.notebook.page_num(self.new_page)
        self.number_list.append(self.number)
        self.number_list.pop()
        self.notebook.show_all()
    
    def on_click_delete(self,action): # # Seçilen bağlantıyı silme fonksiyonu   
        baglantilar_index = list(self.baglantilar.keys()).index(self.labelmenu)
        self.listbox.remove(self.listbox.get_row_at_index(baglantilar_index))  
        self.listbox.show_all()
        self.baglantilar.pop(self.labelmenu)
        self.write_config()               

    def add_newhost_window(self,widget): ## Yeni açılan pencere
        self.input_window = Gtk.Window()
        self.input_window.set_title("Yeni Bağlantı Ekle")
        self.input_window.set_border_width(10)
        self.table2 = Gtk.Table(n_rows=7, n_columns=0, homogeneous=True)
        self.input_window.add(self.table2)

        self.host = Gtk.Entry()
        self.host_name = Gtk.Entry()
        self.user = Gtk.Entry()
        self.port = Gtk.Entry()
        self.submit_button = Gtk.Button("Gönder")
  
        self.host.set_placeholder_text("Host")
        self.host_name.set_placeholder_text("HostName")
        self.user.set_placeholder_text("User")

        self.input_window.add(self.host)
        self.input_window.add(self.host_name)
        self.input_window.add(self.user)
        self.input_window.add(self.port)
        self.input_window.add(self.submit_button)
        self.submit_button.connect('clicked',self.on_click_add_newhost)

        self.table2.attach(self.host,0,1,0,1)
        self.table2.attach(self.host_name,0,1,2,3)
        self.table2.attach(self.user,0,1,4,5)
        self.table2.attach(self.submit_button,0,1,6,7)

        self.input_window.present()
        self.input_window.show_all()  
        
    def listbox_add_items(self): # Listbox'a host isimlerini ekleyen fonksiyon
        self.baglantilar.clear()
        self.read_config()
        keys = self.baglantilar.keys()
        for row in self.listbox.get_children():
            self.listbox.remove(row)
        for i in keys:
            ## label yerine buton oluşturduk
            buttons = Gtk.Button.new_with_label(i)
            buttons.connect("button-press-event",self.button_clicked)
            buttons.connect("button-press-event",self.button_left_click)
            self.listbox.add(buttons) 
        self.listbox.show_all()
    
    def on_click_add_newhost(self,widget): ## Açılır penceredeki gönder butonu fonksiyonu
        self.read_config()
        new_host = self.host.get_text()
        new_hostname = self.host_name.get_text()
        new_user = self.user.get_text()
        default_port = '22'

        self.baglantilar[new_host] = {'Host' : new_host, 'Hostname' : new_hostname , 'User' : new_user, 'Port' : default_port}
        self.write_config()

        self.listbox_add_items()
        self.listbox.show_all()
        self.input_window.hide()

    def _close_cb(self, button): # Kapatma butonu görevi.
        self.notebook.remove_page(self.number_list[-1])
        #self.notebook.show_all()
       
    def close_button(self): # Close butonu
        self._button_box = Gtk.HBox()
        self._button_box.get_style_context().add_class("right")
        self.label1 = Gtk.Label(label=self.labelmenu)

        self._close_btn = Gtk.Button()
        self._close_btn.get_style_context().add_class("titlebutton")
        self._close_btn.get_style_context().add_class("close")

        self._close_btn.add(get_icon("window-close-symbolic"))
        self._close_btn.connect("clicked", self._close_cb)
        
        self._close_btn.show_all()
        self.label1.show_all()
        
        self._button_box.pack_start(self.label1, False, False, 3)
        self._button_box.pack_start(self._close_btn, False, False, 3)
    
    def close_button_2(self):
        self._button_box = Gtk.HBox()
        self._button_box.get_style_context().add_class("right")
        self.label1 = Gtk.Label(label=self.get_host_before)

        self._close_btn = Gtk.Button()
        self._close_btn.get_style_context().add_class("titlebutton")
        self._close_btn.get_style_context().add_class("close")

        self._close_btn.add(get_icon("window-close-symbolic"))
        self._close_btn.connect("clicked", self._close_cb)
        
        self._close_btn.show_all()
        self.label1.show_all()
        
        self._button_box.pack_start(self.label1, False, False, 3)
        self._button_box.pack_start(self._close_btn, False, False, 3)
    
    def index_host(self,wanted_host):#indeksi istenilen hostun labelname atılmalı String
        self.read_config()
        self.wanted_host_index=int()
        
        baglanti_key=list(self.baglantilar.keys())
        for i in range(0,len(baglanti_key)):
            if(baglanti_key[i]==wanted_host):
                self.wanted_host_index=i

    def notebooks(self,labelname): # Attributes sayfası
        self.read_config()
        self.notebook.remove_page(0)
        self.page1 = Gtk.Box()
        self.page1.set_border_width(10)
        self.notebook.prepend_page(self.page1, Gtk.Label("Ana Sayfa"))
        self.notebook.set_current_page(0),
        self.toolbar()
        self.get_host_before = labelname

        grid = Gtk.Grid()
        self.page1.add(grid)
        self.label_dict={}
        self.entries_dict={}
        grid_count=2
        grid_count_2=2
        self.header = Gtk.Label(labelname+" Nitelikleri")
        grid.attach(self.header,0,1,1,1)

        for p_id, p_info in self.baglantilar.items():
                for key in p_info:
                    if(p_info['Host']==labelname):
                        self.labeltemp = "left_label_"+str(key)
                        self.oldlabel = self.labeltemp
                        self.labeltemp = Gtk.Label(key) 
                        self.label_dict[self.oldlabel] = self.labeltemp

                        grid.attach(self.labeltemp,0,grid_count,2,1)
                        grid_count += 1

                        self.temp = "right_entry_"+str(p_info[key])
                        self.oldname = self.temp
                        self.temp = Gtk.Entry()
                        self.entries_dict[self.oldname] = self.temp
                        self.temp.set_text(p_info[key])
                
                        grid.attach(self.temp,5,grid_count_2,2,1)
                        grid_count_2 += 1

        self.add_attribute_button = Gtk.Button("Yeni Nitelik Ekle")
        self.add_attribute_button.connect("clicked",self.add_attribute)

        self.notebook_change_button = Gtk.Button("Niteliği Değiştir")
        self.notebook_change_button.connect('clicked',self.on_click_change)

        self.start_sftp_button = Gtk.Button("SFTP ile Bağlan")
        self.start_sftp_button.connect("clicked",self.on_click_sftp)

        grid.attach(self.add_attribute_button,0,19,2,1)   # Add Attribute button
        grid.attach(self.notebook_change_button,0,20,2,1) # Change butonu 
        grid.attach(self.start_sftp_button,0,21,2,1)      # Start SFTP Button
          
        self.notebook.show_all()
        self.listbox.show_all()
    
    def button_left_click(self,listbox_widget,event): # Buton sol click fonksiyonu
        self.notebooks(listbox_widget.get_label())
        self.notebook.set_current_page(0)
        self.toolbar()
        
    def on_click_change(self,listbox_widget): # Change attribute butonu görevi
        self.values_list = list(self.entries_dict.values())
        self.labels_list = list(self.label_dict.values())
        self.updated_list=dict()
        for i in range(0,len(self.values_list)):
            self.updated_list[self.labels_list[i].get_text()]=self.values_list[i].get_text()
            if self.values_list[i].get_text() == "":
                self.updated_list.pop(self.labels_list[i].get_text())

        self.index_host(self.get_host_before)
        self.baglantilar[self.get_host_before]=self.updated_list
        self.baglantilar[self.values_list[0].get_text()] = self.baglantilar[self.get_host_before]#index değişimi bakılmalı sona eklenen kendi indexsine eklenmeli normalde
        self.write_config()
        self.notebooks(self.values_list[0].get_text())
        self.listbox_add_items()
        self.notebook.set_current_page(0)

    def add_attribute(self,widget): # Yeni attribute penceresi
        self.add_attribute_window = Gtk.Window()
        self.add_attribute_window.set_default_size(10,100)
        self.add_attribute_window.set_title("Nitelik Ekle")
        self.add_attribute_window.set_border_width(10)
        self.table3 = Gtk.Table(n_rows=3, n_columns=5, homogeneous=True)
        self.add_attribute_window.add(self.table3)

        self.attribute_name = Gtk.Entry()
        self.attribute_value = Gtk.Entry()
        self.add_attribute_submit_button = Gtk.Button("Ekle")
  
        self.attribute_name.set_placeholder_text("Nitelik İsmi")
        self.attribute_value.set_placeholder_text("Nitelik Değeri")

        self.add_attribute_window.add(self.attribute_name)
        self.add_attribute_window.add(self.attribute_value)

        self.add_attribute_window.add(self.add_attribute_submit_button)
        self.add_attribute_submit_button.connect('clicked',self.on_click_add_attribute)

        self.table3.attach(self.attribute_name,0,2,0,1)
        self.table3.attach(self.attribute_value,3,5,0,1)

        self.table3.attach(self.add_attribute_submit_button,1,4,2,3)

        self.add_attribute_window.present()
        self.add_attribute_window.show_all() 

        self.notebook.set_current_page(0)

    def on_click_add_attribute(self,widget): # Yeni attribute ekleme butonu görevi
        self.add_attribute_window.hide()
        self.read_config()
        self.baglantilar[self.get_host_before][self.attribute_name.get_text()] = self.attribute_value.get_text()
        self.write_config()
        self.notebooks(self.get_host_before)
        self.notebook.set_current_page(0)

    def enter_password(self):
        self.connect_window = Gtk.Window()
        self.connect_window.set_title("Parola Giriş Ekranı")
        self.connect_window.set_border_width(10)
        self.table4 = Gtk.Table(n_rows=3, n_columns=3, homogeneous=False)
        self.connect_window.add(self.table4)

        self.connect_password = Gtk.Entry()
        self.connect_button = Gtk.Button("Bağlan")
        connect_label = Gtk.Label("Sunucu parolanızı girin.")

        self.connect_password.set_placeholder_text("Parola")
        self.connect_password.set_visibility(False)
        self.connect_window.add(self.connect_password)
        self.connect_window.add(self.connect_button)
        self.table4.attach(connect_label,0,3,0,1)
        #self.table4.attach(connect_label_2,0,2,1,2)
        self.table4.attach(self.connect_password,1,3,1,2)
        self.table4.attach(self.connect_button,1,3,2,3)

        self.connect_window.present()
        self.connect_window.show_all()
        
    def on_click_connect(self,widget): # Sağ tık menüsündeki Connect Host seçeneği ile açılan pencere
        self.enter_password()
        self.connect_button.connect('clicked',self.send_password)
    
    def on_click_sftp(self,widget):
        self.enter_password()
        self.connect_button.connect("clicked",self.sftp_file_transfer)

    def wrong_password_win(self): # Şifre yanlış olduğunda gösterilecek pencere
        self.table5 = Gtk.Table(n_rows=2, n_columns=3, homogeneous=True)
        self.wrong_pass_win = Gtk.Window()
        self.wrong_pass_win.set_title("Wrong")

        self.wrong_pass_label = Gtk.Label("Wrong password ! Try Again.")
        self.wrong_pass_win.add(self.table5)
        self.table5.attach(self.wrong_pass_label,0,3,0,1)

        try_again_button = Gtk.Button("Try Again")
        try_again_button.connect("clicked",self.hide)

        self.table5.attach(try_again_button,1,2,1,2)
        self.wrong_pass_win.show_all()
    
    def hide(self,event):
        self.wrong_pass_win.hide()

    def send_password(self,event): # İlgili makineye login işlemi
        self.terminal2     = Vte.Terminal()
        self.terminal2.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            os.environ[HOME],
            SHELLS,
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,)

        self.new_page = Gtk.Box()
        self.new_page.set_border_width(10)

        self._button_box = Gtk.HBox()
        self._button_box.get_style_context().add_class("right")

        self.close_button()
        self.new_page.add(self.terminal2)
        self.notebook.append_page(self.new_page, self._button_box)

        self.number = self.notebook.page_num(self.new_page)
        self.number_list.append(self.number)
        self.number_list.pop()

        self.aranan = self.baglantilar[self.labelmenu]['Hostname']
        
        self.fp_check = "ssh-keygen -H -F " + self.aranan + " 2>&1 | tee /tmp/control.txt\n"
        self.command = "ssh " + self.labelmenu + " 2>&1 | tee /tmp/control.txt\n"
        self.password = self.connect_password.get_text() + "\n" 

        self.terminal2.feed_child(self.fp_check.encode("utf-8"))
        time.sleep(0.5)
        with open('/tmp/control.txt','r') as t:
            t_list = list()
            t_list = t.readlines()
            length = len(t_list)

            if length > 0:
                self.terminal2.feed_child(self.command.encode("utf-8"))
                time.sleep(0.5) 

                self.terminal2.feed_child(self.password.encode("utf-8"))
                time.sleep(2) 

                self.c_check()
                time.sleep(0.5)

                self.is_correct()
                self.connect_window.hide()
            
            else:
                self.connect_window.hide()
                self.yes_no()

    def yes_no(self):
        self.table8 = Gtk.Table(n_rows=10, n_columns=20, homogeneous=False)
        self.yes_or_no_window = Gtk.Window()
        self.yes_or_no_window.set_default_size(300, 90)
        self.yes_or_no_window.add(self.table8)
        self.yes_or_no_window.set_title("Emin misiniz ? ")

        self.yes_button = Gtk.Button("Devam Et")
        self.table8.attach(self.yes_button,1,10,4,8)
        self.yes_button.connect("clicked",self.yes_button_clicked)
        
        self.no_button = Gtk.Button("Ayrıl")
        self.table8.attach(self.no_button,11,19,4,8)
        self.no_button.connect("clicked",self.no_button_clicked)

        yes_or_no_label = Gtk.Label("     Bu sunucuya ilk kez bağlanıyorsunuz. Devam etmek istediğinize emin misiniz ?  (evet/hayır/[fingerprint])?    ")
        self.table8.attach(yes_or_no_label,0,20,0,2)

        self.yes_or_no_window.show_all()   
    
    def yes_button_clicked(self,event):
        self.terminal2.feed_child(self.command.encode("utf-8"))
        time.sleep(0.5) 

        self.answer = 'yes\n'

        self.terminal2.feed_child(self.answer.encode("utf-8"))
        time.sleep(0.5) 

        self.terminal2.feed_child(self.password.encode("utf-8"))
        time.sleep(2) 

        self.is_correct()
        self.connect_window.hide()
        self.yes_or_no_window.hide()
    
    def no_button_clicked(self,event):
        self.yes_or_no_window.hide()
        self.connect_window.hide()
    
    def c_check(self):
        
        with open('/tmp/control.txt','r') as y:
            string_change = y.read()
            word = "@@@@@@"

            if word in string_change:
                self.connect_window.hide()
                self.host_change()
            
            else:
                pass

    def host_change(self):
        self.host_change_window = Gtk.Window()
        self.host_change_window.set_title("Change known")
        
        self.host_change_entry = Gtk.Entry()
        self.table9 = Gtk.Table(n_rows=1, n_columns=3, homogeneous=True)
        self.host_change_window.add(self.table9)
        self.host_change_entry.set_placeholder_text("Evet değişiklik yap.")

        self.host_change_label = Gtk.Label("Bağlanmak istediğiniz sunucu ip'si başka bir sunucu tarafından alınmış olabilir.\nKnown değişimini onaylıyorsanız --  Evet değişiklik yap  -- yazın")
        self.table9.attach(self.host_change_label,0,3,0,1)
        self.table9.attach(self.host_change_entry,1,2,1,2)

        host_change_button = Gtk.Button("Send")
        host_change_button.connect("clicked",self.hostchange)

        self.table9.attach(host_change_button,1,2,2,3)
        self.host_change_window.show_all()   
        self.notebook.remove_page(-1)
    
    def hostchange(self,event):
        entry = self.host_change_entry.get_text()
        hostname = self.baglantilar[self.labelmenu]['Hostname']
        self.degistir = "ssh-keygen -R " + hostname +"\n"

        if entry.lower() == "evet değişiklik yap":
            self.terminal2.feed_child(self.degistir.encode("utf-8"))
            self.host_change_window.hide()
            self.enter_password()
            self.connect_button.connect('clicked',self.send_password)

    def is_correct(self):
        with open('/tmp/control.txt','r') as correct_file:            
            correct_list = list()
            correct_list = correct_file.readlines()
            length = len(correct_list)
            
            if length > 3:
                self.notebook.show_all()
                self.notebook.set_current_page(-1)
            else:
                self.notebook.remove(self.new_page)
                self.wrong_password_win()
    
    def file_choose(self,event):
        name_list = []
        filechooserdialog = Gtk.FileChooserDialog(title="Göndermek istediğiniz dosyayı seçin.",
             parent=None,
             action=Gtk.FileChooserAction.OPEN)
        filechooserdialog.add_buttons("_Gönder", Gtk.ResponseType.OK)
        filechooserdialog.add_buttons("_Ayrıl", Gtk.ResponseType.CANCEL)
        filechooserdialog.set_default_response(Gtk.ResponseType.OK)

        response = filechooserdialog.run()

        if response == Gtk.ResponseType.OK:
            print("File selected: %s" % filechooserdialog.get_filename())
            self.send_file_path = filechooserdialog.get_filename()
            name_list = self.send_file_path.split('/')
            self.file_name = name_list[-1]
        
        if response == Gtk.ResponseType.CANCEL:
            filechooserdialog.destroy()

        self.transfer()

        filechooserdialog.destroy()
        self.connect_window.hide()
        
    
    def send_file(self,event):
        ssh = SSHClient()
        ssh.load_system_host_keys()

        ip_adress = self.baglantilar[self.labelmenu]['Hostname']
        username = self.baglantilar[self.labelmenu]['User']
        password = self.connect_password.get_text()

        try:
            ssh.connect(ip_adress,username=username,password=password)
            self.connect_window.hide()
            self.choose_file_btn2()
            
        except paramiko.SSHException:
            print("Hata ! ")
            self.connect_window.hide()
            self.scp_transfer("clicked")
    
    def transfer(self):
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ip_adress = self.baglantilar[self.labelmenu]['Hostname']
        username = self.baglantilar[self.labelmenu]['User']
        password = self.connect_password.get_text()
        ssh.connect(ip_adress,username=username,password=password)
        scp = SCPClient(ssh.get_transport())
        scp.put(self.send_file_path, self.file_name)
        scp.close()   
    
    def scp_transfer(self,event):
        self.enter_password()
        self.connect_button.connect('clicked',self.send_file)
        
    def choose_file_btn2(self):
        self.choose_file_winbtn = Gtk.Window()
        self.choose_file_winbtn.set_title("Dosya Seç")
        self.choose_file_winbtn.set_default_size(200, 200)
        self.choose_file_winbtn.set_border_width(20)

        self.table6 = Gtk.Table(n_rows=1, n_columns=1, homogeneous=True)
        self.choose_file_winbtn.add(self.table6)
        
        choose_file_btn_ = Gtk.Button("Dosya Seç")
        self.choose_file_winbtn.add(choose_file_btn_) 
        choose_file_btn_.connect("clicked",self.file_choose)      

        self.table6.attach(choose_file_btn_,0,1,0,1)
        self.choose_file_winbtn.show_all()
        self.connect_window.hide()
    
    def on_search_activated(self,searchentry):
        self.baglantilar.clear()
        self.read_config()
        search_text = searchentry.get_text()
        keys = self.baglantilar.keys()
        for row in self.listbox.get_children():
            self.listbox.remove(row)
        for i in keys:

            if search_text in i:
                deneme_button=Gtk.Button.new_with_label(i)
                deneme_button.connect("button-press-event",self.button_clicked)
                deneme_button.connect("button-press-event",self.button_left_click)
                self.listbox.add(deneme_button)
                
                self.listbox.show_all()
        
    def sftp_file_transfer(self,event):
        self.page1 = Gtk.Box()
        self.page1.set_border_width(10)
        self.table7 = Gtk.Table(n_rows=10, n_columns=30, homogeneous=True)
        self.page1.add(self.table7)
        self._button_box = Gtk.HBox()
        self._button_box.get_style_context().add_class("right")

        self.close_button_2()
        self.deneme_tree()
        self.toolbar()        
 
        self.table7.attach(self.scrollView,0,15,0,10)       
        self.table7.attach(self.scrollView2,16,30,0,10) 
        self.notebook.append_page(self.page1, self._button_box)

        self.number = self.notebook.page_num(self.page1)
        self.number_list.append(self.number)
        self.number_list.pop()
        self.notebook.show_all()
        self.notebook.set_current_page(-1)
    
    def on_drag_data_get(self, widget, drag_context, data, info, time):
        select = widget.get_selection()
        model, treeiter = select.get_selected()
        if treeiter != None:
            print ("drag", model[treeiter][2])#2. eleman yol,0.eleman tutulan dosya adı bunu dataya ver drop kısmında dosya yolunu alıpstfp 
            data.set_text(model[treeiter][2],-1)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        print("girdi")
        model=widget.get_model()
        drop_info = widget.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            print(model[iter][2])
            remotepath=model[iter][2]
            localpath = data.get_text()
            localpath_list = []
            localpath_list = localpath.split('/')
            print("Received text: %s" % localpath)
            print("Received text: %s" % remotepath)


            if os.path.isdir(localpath):  
                self.put_dir(localpath,remotepath) 
            elif os.path.isfile(localpath):  
                remotepathfile=remotepath+"/"+localpath_list[-1]
                self.ftp.put(localpath, remotepathfile) 


            self.deneme_tree()

    def put_dir(self, source, target):
        localpath_list = []
        localpath_list = source.split('/')

        self.ftp.mkdir(target+"/"+localpath_list[-1])
        self.ftp.chdir(target+"/"+localpath_list[-1])
        target=target+"/"+localpath_list[-1]
        for dirpath, dirnames, filenames in os.walk(source):
            remote_path = os.path.join(target, dirpath[len(source)+1:])
            try:
                self.ftp.listdir(remote_path)
            except IOError:
                self.ftp.mkdir(remote_path)

            for filename in filenames:
                self.ftp.put(os.path.join(dirpath, filename), os.path.join(remote_path, filename))
    
    def on_drag_data_get_2(self, widget, drag_context, data, info, time):
        select = widget.get_selection()
        model, treeiter = select.get_selected()
        if treeiter != None:
            print ("drag", model[treeiter][2])#2. eleman yol,0.eleman tutulan dosya adı bunu dataya ver drop kısmında dosya yolunu alıpstfp 
            data.set_text(model[treeiter][2],-1)

    def on_drag_data_received_2(self, widget, drag_context, x, y, data, info, time):
        print("girdi")
        model=widget.get_model()
        drop_info = widget.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            print(model[iter][2])
            remotepath=model[iter][2]
            localpath = data.get_text()
            localpath_list = []
            localpath_list = localpath.split('/')
            print("Received text: %s" % localpath)
            print("Received text: %s" % remotepath)
            remotepath=remotepath+"/"+localpath_list[-1]

            fileattr = self.ftp.lstat(localpath)
            if S_ISDIR(fileattr.st_mode):
                self.download_dir(localpath,remotepath)
            if S_ISREG(fileattr.st_mode):
                self.ftp.get(localpath,remotepath)

            self.deneme_tree()
    
    def download_dir(self,remote_dir, local_dir):
        
        os.path.exists(local_dir) or os.makedirs(local_dir)
        dir_items = self.ftp.listdir_attr(remote_dir) ##
        
        for item in dir_items:

            remote_path = remote_dir + '/' + item.filename         
            local_path = os.path.join(local_dir, item.filename)
            if S_ISDIR(item.st_mode):
                self.download_dir(remote_path, local_path)
            else:
                self.ftp.get(remote_path, local_path)

    def deneme_tree(self):
        fileSystemTreeStore = Gtk.TreeStore(str, Pixbuf, str)
        populateFileSystemTreeStore(fileSystemTreeStore, '/home')
        fileSystemTreeView = Gtk.TreeView(fileSystemTreeStore)
        treeViewCol = Gtk.TreeViewColumn("Ana makina")
        
        colCellText = Gtk.CellRendererText()
        colCellImg = Gtk.CellRendererPixbuf()
        treeViewCol.pack_start(colCellImg, False)
        treeViewCol.pack_start(colCellText, True)
        treeViewCol.add_attribute(colCellText, "text", 0)
        treeViewCol.add_attribute(colCellImg, "pixbuf", 1)
        fileSystemTreeView.append_column(treeViewCol)
        fileSystemTreeView.connect("row-expanded", onRowExpanded)
        fileSystemTreeView.connect("row-collapsed", onRowCollapsed)
        fileSystemTreeView.columns_autosize()
    
        fileSystemTreeView.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, TARGETS, DRAG_ACTION)
        fileSystemTreeView.connect("drag-data-get", self.on_drag_data_get)

        fileSystemTreeView.enable_model_drag_dest(TARGETS, DRAG_ACTION)
        fileSystemTreeView.connect("drag-data-received", self.on_drag_data_received_2)

        self.scrollView = Gtk.ScrolledWindow()
        self.scrollView.set_min_content_width(225)
        self.scrollView.add_with_viewport(fileSystemTreeView)

        sftpURL   =  self.baglantilar[self.get_host_before]['Hostname']
        sftpUser  =  self.baglantilar[self.get_host_before]['User']
        sftpPass  =  self.connect_password.get_text()
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
        
        try:
            ssh.connect(sftpURL, username=sftpUser, password=sftpPass)
            self.ftp = ssh.open_sftp()
            self.connect_window.hide()

        except :
            self.sftp_fail()

        ssh_connect(self.ftp)  
        fileSystemTreeStore2 = Gtk.TreeStore(str, Pixbuf, str)
        populateFileSystemTreeStore2(fileSystemTreeStore2, '/home')
        fileSystemTreeView2 = Gtk.TreeView(fileSystemTreeStore2)
        treeViewCol2 = Gtk.TreeViewColumn("Bağlanılan makina")
        treeViewCol2.set_min_width(225)
   
        colCellText2 = Gtk.CellRendererText()
        colCellImg2 = Gtk.CellRendererPixbuf()
        treeViewCol2.pack_start(colCellImg, False)
        treeViewCol2.pack_start(colCellText, True)
        treeViewCol2.add_attribute(colCellText, "text", 0)
        treeViewCol2.add_attribute(colCellImg, "pixbuf", 1)
        fileSystemTreeView2.append_column(treeViewCol2)
        fileSystemTreeView2.connect("row-expanded", onRowExpanded2)
        fileSystemTreeView2.connect("row-collapsed", onRowCollapsed2)
        select2 = fileSystemTreeView2.get_selection()
        select2.connect("changed", on_tree_selection_changed2)
        fileSystemTreeView2.columns_autosize()

        fileSystemTreeView2.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, TARGETS, DRAG_ACTION)
        fileSystemTreeView2.connect("drag-data-get", self.on_drag_data_get_2)

        fileSystemTreeView2.enable_model_drag_dest(TARGETS, DRAG_ACTION)
        fileSystemTreeView2.connect("drag-data-received", self.on_drag_data_received)

        self.scrollView2 = Gtk.ScrolledWindow()
        self.scrollView2.set_min_content_width(225)
        self.scrollView2.add_with_viewport(fileSystemTreeView2)
    
    def sftp_fail(self):
        self.auth_except_win = Gtk.Window()
        self.auth_except_win.set_title("Fail")
        self.auth_except_win.set_default_size(200, 200)
        self.auth_except_win.set_border_width(20)

        self.table10 = Gtk.Table(n_rows=1, n_columns=1, homogeneous=True)
        self.auth_except_win.add(self.table10)
            
        auth_except_label = Gtk.Label("Auth Failed. Check login informations.")
        self.auth_except_win.add(auth_except_label)       

        self.table10.attach(auth_except_label,0,1,0,1)
        self.auth_except_win.show_all()
        self.connect_window.hide()
    
window = MyWindow()
window.show_all()
Gtk.main()