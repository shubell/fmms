#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" GUI.

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import gtk
import hildon
import logging
log = logging.getLogger('fmms.%s' % __name__)

import fmms_config as fMMSconf
import controller as fMMSController

class fMMS_ConfigDialog():

	def __init__(self, spawner):
		""" Create and display the Configuration dialog. """
		self.config = fMMSconf.fMMS_config()
		
		self.window = spawner
		
		dialog = gtk.Dialog()
		dialog.set_transient_for(self.window)
		dialog.set_title("Configuration")

		allVBox = gtk.VBox()

		labelwidth = 16

		apnHBox = gtk.HBox()
		apn_label = gtk.Label("APN:")
		apn_label.set_width_chars(labelwidth)
		apn_button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		apn_button.set_label("Configure")
		apn_button.connect('clicked', self.show_apn_config, dialog)

		apnHBox.pack_start(apn_label, False, True, 0)
		apnHBox.pack_start(apn_button, True, True, 0)

		numberHBox = gtk.HBox()
		number_label = gtk.Label("Your phonenumber:")
		number_label.set_width_chars(labelwidth)
		self.number = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.number.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_TELE)
		number_text = self.config.get_phonenumber()
		if number_text != None:
			self.number.set_text(number_text)
		else:
			self.number.set_text("")
		numberHBox.pack_start(number_label, False, True, 0)
		numberHBox.pack_start(self.number, True, True, 0)

		imgwidthHBox = gtk.HBox()
		imgwidth_label = gtk.Label("Resize image width:")
		imgwidth_label.set_width_chars(labelwidth)
		self.imgwidth = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.imgwidth.set_max_length(5)
		#self.imgwidth_signal = self.imgwidth.connect('insert_text', self.insert_resize_cb)
		self.imgwidth.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
		imgwidth_text = self.config.get_img_resize_width()
		if imgwidth_text != None:
			self.imgwidth.set_text(str(imgwidth_text))
		else:
			self.imgwidth.set_text("")
		imgwidthHBox.pack_start(imgwidth_label, False, True, 0)
		imgwidthHBox.pack_start(self.imgwidth, True, True, 0)


		expHBox = gtk.HBox()
		exp_label = gtk.Label("Connection mode")
		exp_label.set_width_chars(labelwidth)
		# havoc = CONNMODE_UGLYHACK = 1
		# polite = CONNMODE_ICDSWITCH = 2
		# rude = CONNMODE_FORCESWITCH = 3
		
		hbox = gtk.HButtonBox()
		hbox.set_property("name", "GtkHBox")
		self.havocbutton = hildon.GtkToggleButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.havocbutton.set_label("Havoc")
		self.havocsignal = self.havocbutton.connect('toggled', self.conn_mode_toggled)
		self.rudebutton = hildon.GtkToggleButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.rudebutton.set_label("Rude")
		self.rudesignal = self.rudebutton.connect('toggled', self.conn_mode_toggled)
		self.icdbutton = hildon.GtkToggleButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.icdbutton.set_label("Polite")
		self.icdsignal = self.icdbutton.connect('toggled', self.conn_mode_toggled)
		
		# Set the correct button to be active
		self.connmode_setactive()
		
		hbox.pack_start(self.icdbutton, True, False, 0)
		hbox.pack_start(self.rudebutton, True, False, 0)
		hbox.pack_start(self.havocbutton, True, False, 0)

		alignment = gtk.Alignment(0.5, 0.5, 0, 0)
		alignment.add(hbox)

		expHBox.pack_start(exp_label, False, True, 0)
		expHBox.pack_start(alignment, False, True, 0)

		allVBox.pack_start(apnHBox, False, False, 0)
		allVBox.pack_start(numberHBox, False, False, 0)
		allVBox.pack_start(imgwidthHBox, False, False, 0)
		allVBox.pack_end(expHBox, False, False, 0)

		allVBox.show_all()
		dialog.vbox.add(allVBox)
		dialog.add_button("Save", gtk.RESPONSE_APPLY)
		ret = dialog.run()
		self.config_menu_button_clicked(ret)
		dialog.destroy()

	def show_apn_config(self, button, dialog):
		apndialog = APNConfigDialog(dialog)
		
	def conn_mode_toggled(self, widget):
		""" Ugly hack used since its ToggleButtons """
		self.havocbutton.handler_block(self.havocsignal)
		self.rudebutton.handler_block(self.rudesignal)
		self.icdbutton.handler_block(self.icdsignal)
		if self.havocbutton == widget:
			self.havocbutton.set_active(True)
			self.rudebutton.set_active(False)
			self.icdbutton.set_active(False)
		elif self.rudebutton == widget:
			self.havocbutton.set_active(False)
			self.rudebutton.set_active(True)
			self.icdbutton.set_active(False)
		elif self.icdbutton == widget:
			self.havocbutton.set_active(False)
			self.rudebutton.set_active(False)
			self.icdbutton.set_active(True)
		self.havocbutton.handler_unblock(self.havocsignal)
		self.rudebutton.handler_unblock(self.rudesignal)
		self.icdbutton.handler_unblock(self.icdsignal)
		return True

	def connmode_option(self):
		""" Returns which 'Connection Mode' button is active. """
		if self.havocbutton.get_active():
			return fMMSconf.CONNMODE_UGLYHACK
		elif self.icdbutton.get_active():
			return fMMSconf.CONNMODE_ICDSWITCH
		elif self.rudebutton.get_active():
			return fMMSconf.CONNMODE_FORCESWITCH

	def connmode_setactive(self):
		""" Activate one of the 'Connection Mode' buttons. """
		if self.config.get_connmode() == fMMSconf.CONNMODE_UGLYHACK:
			self.havocbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_ICDSWITCH:
			self.icdbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_FORCESWITCH:
			self.rudebutton.set_active(True)

	def config_menu_button_clicked(self, action):
		""" Checks if we should save the Configuration options. """
		if action == gtk.RESPONSE_APPLY:
			self.config.set_phonenumber(self.number.get_text())
			log.info("Set phonenumber to %s" % self.number.get_text())
			self.config.set_img_resize_width(self.imgwidth.get_text())
			log.info("Set image width to %s" % self.imgwidth.get_text())
			self.config.set_connmode(self.connmode_option())
			log.info("Set connection mode %s" % self.connmode_option())				
			banner = hildon.hildon_banner_show_information(self.window, "", "Settings saved")
			return 0
			
			
class APNConfigDialog():
	
	def __init__(self, parent):
		dialog = gtk.Dialog()
		dialog.set_transient_for(parent)
		dialog.set_title("APN Configuration")
		self.parent = parent
		self.config = fMMSconf.fMMS_config()
		self.cont = fMMSController.fMMS_controller()
		
		allVBox = gtk.VBox()
		
		labelwidth = 16

		inputs = [('Access point name', 'apn'), ('Username', 'user'),
			  ('Password', 'pass'), ('Proxy', 'proxy'), ('Proxy Port', 'proxyport'),
			  ('MMSC', 'mmsc')]
		
		entries = {}
		
		current = self.config.get_apn_settings()

		if not current:
			current = self.cont.get_apn_settings_automatically()
			self.config.set_apn_settings(current)
			log.info("Set APN settings: %s" % current)
		
		if current['apn'] == "":
			current = self.cont.get_apn_settings_automatically()
			self.config.set_apn_settings(current)
			log.info("Set APN settings: %s" % current)
		
		for labelname in inputs:
			(labelname, var) = labelname
			box = gtk.HBox()
			label = gtk.Label(labelname)
			label.set_width_chars(labelwidth)
			vars()[var] = gtk.Entry()
			if current:
				if current[var]:
					vars()[var].set_text(str(current[var]))
			entries[var] = vars()[var]
			box.pack_start(label, False, True, 0)
			box.pack_start(vars()[var], True, True, 0)
			allVBox.pack_start(box, False, False, 2)

		button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		button.set_label("Advanced")
		button.connect('clicked', self.create_advanced_config, dialog)
		allVBox.pack_end(button, False, False, 2)

		allVBox.show_all()
		dialog.vbox.add(allVBox)
		dialog.add_button("Save", gtk.RESPONSE_APPLY)
		ret = dialog.run()
		
		settings = {}
		for val in entries:
			settings[val] = vars()[val].get_text()
		
		if ret == gtk.RESPONSE_APPLY:
			self.config.set_apn_settings(settings)
			log.info("Set APN settings: %s" % settings)
			banner = hildon.hildon_banner_show_information(parent, "", "APN settings saved")
		
		dialog.destroy()
		
	def create_advanced_config(self, widget, spawnedby):
		dialog = gtk.Dialog()
		dialog.set_title("Advanced Configuration")

		allVBox = gtk.VBox()

		labelwidth = 16

		inputs = [('IP', 'ip'), ('Primary DNS', 'pdns'), ('Secondary DNS', 'sdns')]

		entries = {}
		
		current = self.config.get_advanced_apn_settings()
		
		if not current:
			current = self.cont.get_apn_settings_automatically()
			self.config.set_advanced_apn_settings(settings)
			log.info("Set Advanced APN settings: %s" % settings)
				
		if current['ip'] == "":
			current = self.cont.get_apn_settings_automatically()
			self.config.set_advanced_apn_settings(settings)
			log.info("Set Advanced APN settings: %s" % settings)

		for labelname in inputs:
			(labelname, var) = labelname
			box = gtk.HBox()
			label = gtk.Label(labelname)
			label.set_width_chars(labelwidth)
			vars()[var] = gtk.Entry()
			if current[var]:
				vars()[var].set_text(str(current[var]))
			entries[var] = vars()[var]
			box.pack_start(label, False, True, 0)
			box.pack_start(vars()[var], True, True, 0)
			allVBox.pack_start(box, False, False, 2)

		allVBox.show_all()
		dialog.vbox.add(allVBox)
		dialog.add_button("Save", gtk.RESPONSE_APPLY)
		ret = dialog.run()
		
		settings = {}
		for val in entries:
			settings[val] = vars()[val].get_text()

		if ret == gtk.RESPONSE_APPLY:
			self.config.set_advanced_apn_settings(settings)
			log.info("Set Advanced APN settings: %s" % settings)
			banner = hildon.hildon_banner_show_information(self.parent, "", "Advanced settings saved")

		dialog.destroy()
		
if __name__ == "__main__":
	fMMS_ConfigDialog(None)