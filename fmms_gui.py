#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Main-view UI for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os
import time

import gtk
import hildon
import osso
import gobject
import dbus
from gnome import gnomevfs

from wappushhandler import PushHandler
import fmms_config as fMMSconf
import fmms_sender_ui as fMMSSenderUI
import fmms_viewer as fMMSViewer
import controller as fMMSController
import contacts as ContactH

class fMMS_GUI(hildon.Program):

	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self.ch = ContactH.ContactHandler()
		self.osso_c = osso.Context("fMMS", "0.1.0", False)
	
		if not os.path.isdir(self._mmsdir):
			print "creating dir", self._mmsdir
			os.makedirs(self._mmsdir)
		if not os.path.isdir(self._pushdir):
			print "creating dir", self._pushdir
			os.makedirs(self._pushdir)
	
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
		
		self.osso_rpc = osso.Rpc(self.osso_c)
      		self.osso_rpc.set_rpc_callback("se.frals.fmms","/se/frals/fmms","se.frals.fmms", self.cb_open_fmms, self.osso_c)
		
		self.window = hildon.StackableWindow()
		self.window.set_title("fMMS")
		program.add_window(self.window)
		
		self.window.connect("delete_event", self.quit)
		
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
		
		
		### TODO: dont hardcode the values here.. oh well
		iconcell = gtk.CellRendererPixbuf()
		photocell = gtk.CellRendererPixbuf()
		textcell = gtk.CellRendererText()
		iconcell.set_fixed_size(48, 64)
		cell2 = gtk.CellRendererText()
		cell2.set_property('xalign', 1.0)
		photocell.set_property('xalign', 1.0)
		photocell.set_fixed_size(64, 64)
		textcell.set_property('mode', gtk.CELL_RENDERER_MODE_INERT)
		textcell.set_fixed_size(650, 64)
		textcell.set_property('xalign', 0.0)
		
		self.liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, str)
		self.treeview = hildon.GtkTreeView(gtk.HILDON_UI_MODE_EDIT)
		self.treeview.set_model(self.liststore)

		
		icon_col = gtk.TreeViewColumn('Icon')
		sender_col = gtk.TreeViewColumn('Sender')
		placeholder_col = gtk.TreeViewColumn('Photo')
		
		
		self.add_buttons_liststore()
		
		self.treeview.append_column(icon_col)
		self.treeview.append_column(sender_col)
		self.treeview.append_column(placeholder_col)
		
		icon_col.pack_start(iconcell, False)
		icon_col.set_attributes(iconcell, pixbuf=0)
		sender_col.pack_start(textcell, True)
		sender_col.set_attributes(textcell, markup=1)
		placeholder_col.pack_end(photocell, False)
		placeholder_col.set_attributes(photocell, pixbuf=2)
		
		selection = self.treeview.get_selection()
		#selection.set_mode(gtk.SELECTION_SINGLE)
		self.treeview.connect('hildon-row-tapped', self.show_mms)
		
		
		self.liststore_menu = self.liststore_mms_menu()
		self.treeview.tap_and_hold_setup(self.liststore_menu)
		#treeview.connect('tap-and-hold', self.liststore_mms_clicked)
		
		
		pan.add_with_viewport(self.treeview)
		self.window.add(pan)
	
		self.menu = self.create_menu()
		self.window.set_app_menu(self.menu)
		
		self.window.connect('focus-in-event', self.cb_on_focus)
		
		self.window.show_all()
		self.add_window(self.window)
		
		if self.config.get_firstlaunch() == 1:
			print "firstlaunch"
			note = osso.SystemNote(self.osso_c)
			firstlaunchmessage = "NOTE: Currently you have to connect manually to the MMS APN when sending and receiving.\nAlso, only implemented attachment is image."
			note.system_note_dialog(firstlaunchmessage , 'notice')
			self.create_config_dialog()
			self.config.set_firstlaunch(0)
	
	def cb_on_focus(self, widget, event):
		self.liststore.clear()
		self.add_buttons_liststore()
	
	def cb_open_fmms(self, interface, method, args, user_data):
		if method != 'open_mms' and method != 'open_gui':
			return
		if method == 'open_mms':
			filename = args[0]
			if self.cont.is_fetched_push_by_transid(filename):
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
				banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Opening message")
				self.force_ui_update()
				viewer = fMMSViewer.fMMS_Viewer(filename)
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
				return
			else:
				return
		elif method == 'open_gui':
			print "open_gui called"
			self.liststore.clear()
			self.add_buttons_liststore()
			return
		
	def create_menu(self):
		menu = hildon.AppMenu()
		
		send = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		send.set_label("New MMS")
		send.connect('clicked', self.menu_button_clicked)
		
		config = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		config.set_label("Configuration")
		config.connect('clicked', self.menu_button_clicked)
		
		about = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		about.set_label("About")
		about.connect('clicked', self.menu_button_clicked)
		
		menu.append(send)
		menu.append(config)
		menu.append(about)
		
		menu.show_all()
		
		return menu
		
	def menu_button_clicked(self, button):
		buttontext = button.get_label()
		if buttontext == "Configuration":
			ret = self.create_config_dialog()
		elif buttontext == "New MMS":
			ret = fMMSSenderUI.fMMS_GUI(self.window).run()
		elif buttontext == "About":
			ret = self.create_about_dialog()
		
	def create_about_dialog(self):
		dialog = gtk.AboutDialog()                                                 
		dialog.set_name("fMMS")
		fmms_logo = gtk.gdk.pixbuf_new_from_file("/opt/fmms/fmms.png")
		dialog.set_logo(fmms_logo)                                   
		dialog.set_comments('MMS send and receive support for Fremantle')                      
		dialog.set_version(self.config.get_version())                                                
		dialog.set_copyright("By Nick Leppänen Larsson (aka frals)")                    
		dialog.set_website("http://mms.frals.se/")                                  
		dialog.connect("response", lambda d, r: d.destroy())                      
		dialog.show() 
 
	def create_config_dialog(self):
		dialog = gtk.Dialog()
		dialog.set_title("Configuration")
		
		allVBox = gtk.VBox()
		
		self.active_apn_index = 0
		
		apnHBox = gtk.HBox()
		apn_label = gtk.Label("APN:")
		self.selector = self.create_apn_selector()
		self.apn = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		self.apn.set_selector(self.selector)
		self.apn.set_active(self.active_apn_index)

		apnHBox.pack_start(apn_label, False, True, 0)
		apnHBox.pack_start(self.apn, True, True, 0)
		
		mmscHBox = gtk.HBox()
		mmsc_label = gtk.Label("MMSC:")
		self.mmsc = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		mmsc_text = self.config.get_mmsc()
		if mmsc_text != None:	
			self.mmsc.set_text(mmsc_text)
		else:
			self.mmsc.set_text("http://")
		mmscHBox.pack_start(mmsc_label, False, True, 0)
		mmscHBox.pack_start(self.mmsc, True, True, 0)
		
		numberHBox = gtk.HBox()
		number_label = gtk.Label("Your phonenumber:")
		self.number = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		number_text = self.config.get_phonenumber()
		if number_text != None:
			self.number.set_text(number_text)
		else:
			self.number.set_text("")
		numberHBox.pack_start(number_label, False, True, 0)
		numberHBox.pack_start(self.number, True, True, 0)
		
		imgwidthHBox = gtk.HBox()
		imgwidth_label = gtk.Label("Resize image width:")
		self.imgwidth = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		imgwidth_text = self.config.get_img_resize_width()
		if imgwidth_text != None:
			self.imgwidth.set_text(str(imgwidth_text))
		else:
			self.imgwidth.set_text("")
		imgwidthHBox.pack_start(imgwidth_label, False, True, 0)
		imgwidthHBox.pack_start(self.imgwidth, True, True, 0)
		
		notelabel = gtk.Label("APN refers to the name of the connection in\n \"Internet Connections\" to use.")
		
		allVBox.pack_start(notelabel, False, True, 0)
		allVBox.pack_start(apnHBox, False, False, 0)
		allVBox.pack_start(mmscHBox, False, False, 0)
		allVBox.pack_end(numberHBox, False, False, 0)
		allVBox.pack_end(imgwidthHBox, False, False, 0)
		
		allVBox.show_all()
		dialog.vbox.add(allVBox)
		dialog.add_button("Save", gtk.RESPONSE_APPLY)
		while 1:
			ret = dialog.run()
			ret2 = self.config_menu_button_clicked(ret)
			if ret2 == 0 or ret2 == None: 
				break
			
		dialog.destroy()
		return ret


	""" selector for apn """
	def create_apn_selector(self):
		selector = hildon.TouchSelector(text = True)
		apnlist = self.config.get_gprs_apns()
		currval = self.config.get_apn_nicename()
		# Populate selector
		i = 0
		for apn in apnlist:
			if apn != None:
				if apn == currval:
					self.active_apn_index = i
				i += 1	
				# Add item to the column 
				selector.append_text(apn)
			
		selector.center_on_selected()
		selector.set_active(0, i)
		# Set selection mode to allow multiple selection
		selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
		return selector
		
		
	def config_menu_button_clicked(self, action):
		if action == gtk.RESPONSE_APPLY:
			print self.apn.get_selector().get_current_text()
			ret_setapn = self.config.get_apnid_from_name(self.apn.get_selector().get_current_text())
			if ret_setapn != None:
				self.config.set_apn(ret_setapn)
				print "Set apn to: %s" % ret_setapn
				ret = self.config.set_mmsc(self.mmsc.get_text())
				print "Set mmsc to %s" % self.mmsc.get_text()
				self.config.set_phonenumber(self.number.get_text())
				print "Set phonenumber to %s" % self.number.get_text()
				self.config.set_img_resize_width(self.imgwidth.get_text())
				print "Set image width to %s" % self.imgwidth.get_text()
				banner = hildon.hildon_banner_show_information(self.window, "", "Settings saved")
				return 0
			else:
				print "Set mmsc to %s" % self.mmsc.get_text()
				self.config.set_phonenumber(self.number.get_text())
				print "Set phonenumber to %s" % self.number.get_text()
				self.config.set_img_resize_width(self.imgwidth.get_text())
				print "Set image width to %s" % self.imgwidth.get_text()
				banner = hildon.hildon_banner_show_information(self.window, "", "Could not save APN settings. Did you enter a correct APN?")
				banner.set_timeout(5000)
				return -1
		

	""" add each item to our liststore """
	def add_buttons_liststore(self):
			icon_theme = gtk.icon_theme_get_default()
			
			pushlist = self.cont.get_push_list()
			for varlist in pushlist:
				mtime = varlist['Time']
				fname = varlist['Transaction-Id']
				direction = self.cont.get_direction_mms(fname)
				# TODO Use fancy icon for showing read/unread
				
				
				if self.cont.is_mms_read(fname):
					isread = " (Read)"
				else:
					isread = " (Unread)"
				
				
				try:
					sender = varlist['From']
					sender = sender.replace("/TYPE=PLMN", "")
				except:
					sender = "0000000"
				
				if direction == fMMSController.MSG_DIRECTION_OUT:
					sender = "You (Outgoing)"
				
				sendername = self.ch.get_name_from_number(sender)
				photo = icon_theme.load_icon("general_default_avatar", 48, 0)
				if sendername != None:
					sender = sendername + ' <span size="smaller">(' + sender + ')</span>'
					phototest = self.ch.get_photo_from_name(sendername, 64)
					if phototest != None:	
						photo = phototest
						#print "loaded photo:", photo.get_width(), photo.get_height()
	
				#title = sender + " - " + mtime
				
				if self.cont.is_fetched_push_by_transid(fname):
					icon = icon_theme.load_icon("general_sms", 48, 0)
				else:
					icon = icon_theme.load_icon("chat_unread_sms", 48, 0)
				self.liststore.append([icon, sender + isread + '  <span foreground="#666666" size="smaller"><sup>' + mtime + '</sup></span>\n<span foreground="#666666" size="x-small">' + fname + '</span>', photo, fname])
	
	""" lets call it quits! """
	def quit(self, *args):
		gtk.main_quit()
	
	
	""" forces ui update, kinda... god this is AWESOME """
	def force_ui_update(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
		
		
	""" delete push message """
	def delete_push(self, fname):
		self.cont.delete_push_message(fname)
		
	
	""" delete mms message (eg for redownload) """
	def delete_mms(self, fname):
		self.cont.delete_mms_message(fname)
	
	""" delete push & mms """
	def delete_push_mms(self, fname):
		try:
			self.cont.wipe_message(fname)
			banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Message deleted")
		except Exception, e:
			print "Exception caught:"
			print type(e), e
			raise
			banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Failed to delete message.")


	""" action on delete contextmenu click """
	def liststore_delete_clicked(self, widget):
		dialog = gtk.Dialog()
		dialog.set_title("Confirm")
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label("Are you sure you want to delete the message?")
		dialog.vbox.add(label)
		dialog.show_all()
		ret = dialog.run()
		if ret == 1:
			(model, miter) = self.treeview.get_selection().get_selected()
			# the 4th value is the filename (start counting at 0)
			filename = model.get_value(miter, 3)
			print "deleting", filename
			self.delete_push_mms(filename)
			self.liststore.remove(miter)
		dialog.destroy()
		return
	
	""" action on redl contextmenu click """
	def liststore_redl_clicked(self, widget):
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		dialog = gtk.Dialog()
		dialog.set_title("WARNING")
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label("If the message is no longer on your MMSC,\n the message will be lost. Continue?")
		dialog.vbox.add(label)
		dialog.show_all()
		ret = dialog.run()
		dialog.destroy()
		self.force_ui_update()
		
		if ret == 1:
			(model, miter) = self.treeview.get_selection().get_selected()
			# the 4th value is the filename (start counting at 0)
			filename = model.get_value(miter, 3)
			print "redownloading", filename
			try:
				self.delete_mms(filename)
				banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Trying to download MMS...")
				self.force_ui_update()
				
				# TODO: FIXME
				
				self.cont.get_mms_from_push(filename)
				self.show_mms(self.treeview, model.get_path(miter))
			except Exception, e:
				print type(e), e
				#raise
				banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Operation failed")
			hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		return

	""" long press on image creates this """
	def liststore_mms_menu(self):
		menu = gtk.Menu()
		menu.set_title("hildon-context-sensitive-menu")

		redlItem = gtk.MenuItem("Redownload")
		menu.append(redlItem)
		redlItem.connect("activate", self.liststore_redl_clicked)
		redlItem.show()
		
		separator = gtk.MenuItem()
		menu.append(separator)
		separator.show()
		
		openItem = gtk.MenuItem("Delete")
		menu.append(openItem)
		openItem.connect("activate", self.liststore_delete_clicked)
		openItem.show()
		
		menu.show_all()
		return menu

	""" show the selected mms """		
	def show_mms(self, treeview, path):
		# Show loading indicator
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Opening message")
		self.force_ui_update()
		
		print path
		model = treeview.get_model()
		miter = model.get_iter(path)
		# the 4th value is the transactionid (start counting at 0)
		transactionid = model.get_value(miter, 3)
		
		try:
			viewer = fMMSViewer.fMMS_Viewer(transactionid)
		except Exception, e:
			print type(e), e
			#raise
		
		
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)

	def run(self):
		self.window.show_all()
		gtk.main()
		
if __name__ == "__main__":
	app = fMMS_GUI()
	app.run()