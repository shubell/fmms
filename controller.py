#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import logging
import logging.config

logging.config.fileConfig('/opt/fmms/logger.conf')
log = logging.getLogger('fmms.%s' % __name__)

import os
import array
import re
import time
import urlparse
import subprocess
import gettext
import socket

import dbus

import fmms_config as fMMSconf
import dbhandler as DBHandler
from mms.message import MMSMessage
from mms import mms_pdu
from wappushhandler import MMSSender

#TODO: constants.py?
MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1

_ = gettext.gettext
gettext.bindtextdomain('fmms','/opt/fmms/share/locale/')
gettext.textdomain('fmms')

class fMMS_controller():
	
	def __init__(self):
		""" initialize """
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._outdir = self.config.get_outdir()
		self.store = DBHandler.DatabaseHandler(self)
		self.ui = False
	
	def clean_url(self, url):
		m = re.search(r"http\:\/\/(?i)", url)
		if m:
			url = url.replace(m.group(0), "http://")
		return url
	
	def get_host_from_url(self, url):
		""" gets the hostname from an url """
		# change HTTP:// etc to lowercase because
		# havoc connector depends on it
		url = self.clean_url(url)
		if not url.startswith("http://"):
			url = "http://%s" % url

		ret = urlparse.urlparse(url)
		ret = ret[1].split(":")[0]
		return ret
	
	def convert_to_real_ip(self, indata):
		""" converts a ip with leading zeroes to a real ip """
		# Check if it looks like an IP
		if re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", indata):
			ip = indata.split(".")
			dot = "."
			final = []
			for octet in ip:
				final.append(str(int(octet)))
			indata = dot.join(final)
		return indata
	
	def convert_timeformat(self, intime, format, hideToday=False):
		mtime = intime
		try:
			mtime = time.strptime(mtime, "%Y-%m-%d %H:%M:%S")
		except ValueError, e:
			#log.info("timeconversion stage1 failed: %s %s", type(e), e)
			try:
				mtime = time.strptime(mtime)
			except ValueError, e:
				#log.info("timeconversion stage2 failed: %s %s", type(e), e)
				pass
		except Exception, e:
			#log.exception("Could not convert timestamp: %s %s", type(e), e)
			pass
		
		# TODO: check if hideToday == true
		# TODO: remove date if date == today
		try:
			mtime = time.strftime("%Y-%m-%d | %H:%M", mtime)
		except:
			log.info("stftime failed: %s %s", type(e), e)
			mtime = intime
		return mtime
	
	def send_mms(self, to, subject, message, attachment, sender):
		try:
			sender = MMSSender(to, subject, message, attachment, sender, setupConn=True, controller=self)
		except:
			msg = "%s" % (gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed"))
			return (-1, msg)
		try:
			(status, reason, output, parsed) = sender.sendMMS()

			if parsed == True and "Response-Status" in output:
				if output['Response-Status'] == "Ok":
					log.info("message seems to have sent AOK!")
					return (0, "OK")

			errstr = gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed")
			message = str(status) + "_" + str(reason)
			reply = str(output)
			msg = "%s\nMMSC: %s\nBODY: %s" % (errstr, message, reply)
			return (-1, msg)
		except socket.error, exc:
			log.exception("sender failed due to connection error")
			errstr = gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed")
			errhelp = _("Please check your settings.")
			msg = "%s\n%s\n%s" % (errstr, exc, errhelp)
			return (-1, msg)
			#raise
		except Exception, exc:
			log.exception("Sender failed.")
			msg = "%s\n%s" % (gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed"), exc)
			return (-1, msg)
			#raise
	
	def decode_mms_from_push(self, binarydata):
		""" decodes the given mms """
		decoder = mms_pdu.MMSDecoder()
		wsplist = decoder.decodeCustom(binarydata)
		sndr, url, trans_id = None, None, None

		try:
			url = wsplist["Content-Location"]
			log.info("content-location: %s", url)
			trans_id = wsplist["Transaction-Id"]
			trans_id = str(trans_id)
			log.info("transid: %s", trans_id)
		except Exception, e:
			log.exception("no content-location/transid in push; aborting: %s %s", type(e), e)
			bus = dbus.SystemBus()
			proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
			interface = dbus.Interface(proxy, dbus_interface='org.freedesktop.Notifications')
			interface.SystemNoteInfoprint(gettext.ldgettext('modest', "mail_ni_ui_folder_get_msg_folder_error"))
			raise
		try:
			sndr = wsplist["From"]
			log.info("Sender: %s", sndr)
		except Exception, e:
			log.exception("No sender value defined: %s %s", type(e), e)
			sndr = "Unknown sender"

		self.save_binary_push(binarydata, trans_id)
		return (wsplist, sndr, url, trans_id)
	
	def save_binary_push(self, binarydata, transaction):
		""" saves the binary push message """
		data = array.array('B')
		for b in binarydata:
			data.append(b)

		try:
			fp = open(self._pushdir + transaction, 'wb')
			fp.write(data)
			log.info("saved binary push: %s", fp)
			fp.close()
		except Exception, e:
			log.exception("failed to save binary push")
			raise
	
	def save_push_message(self, data):
		""" Gets the decoded data as a list (preferably from decode_mms_from_push)
		"""
		pushid = self.store.insert_push_message(data)
		return pushid
	
	def get_push_list(self, types=None):
		""" gets a list of all push messages """
		return self.store.get_push_list()
	
	def is_fetched_push_by_transid(self, transactionid):
		return self.store.is_mms_downloaded(transactionid)
	
	def read_push_as_list(self, transactionid):
		return self.store.get_push_message(transactionid)
	
	def save_binary_mms(self, data, transaction):
		dirname = self._mmsdir + transaction
		if not os.path.isdir(dirname):
			os.makedirs(dirname)
		
		fp = open(dirname + "/message", 'wb')
		fp.write(data)
		log.info("saved binary mms %s", fp)
		fp.close()
		return dirname
		
	def save_binary_outgoing_mms(self, data, transaction):
		transaction = str(transaction)
		dirname = self._outdir + transaction
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		fp = open(dirname + "/message", 'wb')
		fp.write(data)
		log.info("saved binary mms %s", fp)
		fp.close()
		return dirname
	
	def decode_binary_mms(self, path):
		""" decodes and saves the binary mms"""
		# Decode the specified file
		# This also creates all the parts as files in path
		log.info("decode_binary_mms running: %s", str(path))
		try:
			message = MMSMessage.fromFile(path + "/message")
		except Exception, e:
			log.exception("decode binary failed:", type(e), e)
			raise
		log.info("returning message!")
		return message
	
	def get_filepath_for_mms_transid(self, filename):
		return self.store.get_filepath_for_mms_transid(filename).replace("/message", "")
	
	def is_mms_read(self, transactionid):
		return self.store.is_message_read(transactionid)
	
	def mark_mms_read(self, transactionid):
		self.store.mark_message_read(transactionid)
	
	def store_mms_message(self, pushid, message, transactionId=None):
		if transactionId:
			message.headers['Transaction-Id'] = transactionId
		mmsid = self.store.insert_mms_message(pushid, message)
		return mmsid
	
	def store_outgoing_mms(self, message):
		mmsid = self.store.insert_mms_message(0, message, DBHandler.MSG_DIRECTION_OUT)
		return mmsid
		
	def store_outgoing_push(self, wsplist):
		pushid = self.store.insert_push_send(wsplist)
		return pushid
		
	def link_push_mms(self, pushid, mmsid):
		self.store.link_push_mms(pushid, mmsid)
	
	def get_direction_mms(self, transid):
		return self.store.get_direction_mms(transid)
		
	def get_replyuri_from_transid(self, transid):
		uri = self.store.get_replyuri_from_transid(transid)
		try:
			uri = uri.replace("/TYPE=PLMN", "")
			return uri
		except Exception, e:
			log.exception("failed to get replyuri, got: %s (%s)", uri, uri.__class__)
			return ""
	
	def get_mms_from_push(self, transactionid):
		plist = self.store.get_push_message(transactionid)
		#trans_id = plist['Transaction-Id']
		# lets reuse the transactionid we already got
		trans_id = transactionid
		pushid = plist['PUSHID']
		url = plist['Content-Location']
		
		from wappushhandler import PushHandler
		p = PushHandler()
		path = p._get_mms_message(url, trans_id, self)
		log.info("path: %s", path)
		print trans_id
		os.system("if [ ! -f /home/user/.fmms/mms/" + trans_id + "/message.bak ]; then cp /home/user/.fmms/mms/" + trans_id + "/message /home/user/.fmms/mms/" + trans_id + "/message.bak; fi")
		message = self.decode_binary_mms(path)
		os.system("if [ -f /home/user/.fmms/mms/" + trans_id + "/message.bak ]; then diff /home/user/.fmms/mms/" + trans_id + "/message /home/user/.fmms/mms/" + trans_id + "/message.bak; if [ \"$?\" == \"0\" ]; then rm /home/user/.fmms/mms/" + trans_id + "/message.bak; fi; fi")
		log.info("storing mms...%s", trans_id)
		mmsid = self.store_mms_message(pushid, message, transactionId=trans_id)
		
	def get_mms_attachments(self, transactionid, allFiles=False):
		return self.store.get_mms_attachments(transactionid, allFiles)
	
	def get_mms_headers(self, transactionid):
		return self.store.get_mms_headers(transactionid)
	
	def delete_mms_message(self, fname):
		fullpath = self.store.get_filepath_for_mms_transid(fname)
		if fullpath:
			fullpath = fullpath.replace("/message", "")
		else:
			fullpath = self._mmsdir + fname

		log.info("fullpath: %s", fullpath)
		if os.path.isdir(fullpath):
			log.info("starting deletion of %s", fullpath)
			filelist = os.listdir(fullpath)
			log.info("removing: %s", filelist)
			for fn in filelist:
				try:
					fullfn = fullpath + "/" + fn
					os.remove(fullfn)
				except:
					log.info("failed to remove: %s", fullfn)
			try:
				log.info("trying to remove: %s", fullpath)
				os.rmdir(fullpath)
			except OSError, e:
				log.exception("failed to remove: %s %s", type(e), e)
				raise
		
		self.store.delete_mms_message(fname)
		
	def delete_push_message(self, fname):
		fullpath = self.store.get_filepath_for_push_transid(fname)
		if not fullpath:
			fullpath = self._pushdir + fname

		log.info("fullpath: %s", fullpath)
		if os.path.isfile(fullpath):
			log.info("removing: %s", fullpath)
			try:
				os.remove(fullpath)
			except Exception, e:
				log.exception("%s %s", type(e), e)
				raise
		self.store.delete_push_message(fname)
		
	def wipe_message(self, transactionid):
		self.delete_mms_message(transactionid)
		self.delete_push_message(transactionid)
	
	def save_draft(self, rcpt, text, attachment):
		if not rcpt:
			rcpt = ""
		if not text:
			text = ""
		if not attachment:
			attachment = ""
		self.store.save_draft(rcpt, text, attachment)

	def get_draft(self):
		return self.store.get_draft()

	def validate_phonenumber_email(self, nr):
		nr = str(nr)
		nr = nr.replace("+", "")
		nr = nr.replace(" ", "")
		if re.search(r"(\D)+", nr) == None or "@" in nr or ";" in nr:
			return True
		else:
		 	return False
		
	def get_mcc_mnc(self):
		""" Gets the SIM cards MMC/MNC """
		bus = dbus.SystemBus()
		phone = dbus.Interface(bus.get_object("com.nokia.phone.SIM", "/com/nokia/phone/SIM"), "Phone.Sim")
		hplmn = phone.read_hplmn()
		(mcc, thirdbytes, mnc) = hplmn[0]
		# extract 4 lowest bits (as integer)
		mcc1 = int(mcc) & 0xF
		# and 4 highest bits (as integer)
		mcc2 = int(mcc) >> 4
		# 4 lowest bits of the "united" byte is mcc3
		mcc3 = int(thirdbytes) & 0xF
		# 4 lowest bits of mnc is mnc1
		mnc1 = int(mnc) & 0xF
		# 4 highest bits of mnc is mnc2
		mnc2 = int(mnc) >> 4
		# if 4 highest bits of "united" byte is
		# 0xf only 2 digits are used for mnc
		mnc3 = int(thirdbytes) >> 4

		if mnc3 == 0xf:
			final_mnc = "%s%s" % (mnc1, mnc2)
		else:
			final_mnc = "%s%s%s" % (mnc1, mnc2, mnc3)

		final_mcc = "%s%s%s" % (mcc1, mcc2, mcc3)
		
		return final_mcc, final_mnc

	def get_current_connection_iap_id(self):
		bus = dbus.SystemBus()
		icd = dbus.Interface(bus.get_object("com.nokia.icd", "/com/nokia/icd"), "com.nokia.icd")
		(iap, ign, ign, ign, ign, ign, ign) = icd.get_statistics()
		return iap

	def disconnect_current_connection(self):
		args = "DISCONNECT"
		retcode = subprocess.call(["/opt/fmms/fmms_magic", args])

	def get_operator_display_name(self):
		bus = dbus.SystemBus()
		phone = dbus.Interface(bus.get_object("com.nokia.phone.SIM", "/com/nokia/phone/SIM"), "Phone.Sim")
		(providername, ign, ign2, err) = phone.get_service_provider_name()
		return providername

	def get_settings_from_file(self, mcc, mnc, displayname):
		fn = open("/etc/operator_settings", 'r')
		mcc = str(int(mcc))
		mnc = str(int(mnc))
		for line in fn:
			"""
			0 : MCC
			1 : MNC
			2 : SERVICE PROVIDER NAME
			3 : ACCESS TYPE
			4 : IAP NAME
			5 : GPRS ACCESSPOINT NAME
			6 : GPRS AUTOLOGIN (X = YES)
			7 : USERNAME
			8 : PASSWORD
			9 : <empty>
			10 : <empty>
			11 : GPRS MMS/WAP GATEWAY PROXY
			12 : GPRS MMS/WAP GATEWAY PORT
			13 : IP ADDRESS (IF NOT FETCHED FROM SERVER)
			14 : PRIMARY DNS ADDRESS (IF NOT FETCHED FROM SERVER)
			15 : SECONDARY DNS ADDRESS (IF AVAILABLE)
			16 : <empty>
			"""
			row = line.split('\t')
			if row[0] == mcc and row[1] == mnc and row[3] == 'MMS' and displayname.lower() in row[2].lower():
				settings = {}
				settings['apn'] = row[5]
				settings['user'] = row[7]
				settings['pass'] = row[8]
				settings['proxy'] = row[11]
				settings['proxyport'] = row[12]
				settings['ip'] = row[13]
				settings['pdns'] = row[14]
				settings['sdns'] = row[15]
				settings['mmsc'] = row[17]
				return settings
		return None

	def get_apn_settings_automatically(self):
		(mcc, mnc) = self.get_mcc_mnc()
		operatorname = self.get_operator_display_name()
		settings = self.get_settings_from_file(mcc, mnc, operatorname)
		
		if self.are_we_tele2_se(mcc, mnc, operatorname):
			settings = self.are_we_tele2_se(mcc, mnc, operatorname)
		
		log.info("Settings loaded automatically. MCC: %s MNC: %s Operatorname: %s" % (mcc, mnc, operatorname))
		log.info("Settings loaded automatically: %s" % settings)
		return settings
	
	def are_we_tele2_se(self, mcc, mnc, operatorname):
		mcc = str(int(mcc))
		mnc = str(int(mnc))
		if mcc == "240" and mnc == "7":
			if "Tele2" in operatorname:
				settings = {}
				settings['apn'] = "internet.tele2.se"
				settings['user'] = ""
				settings['pass'] = ""
				settings['proxy'] = "130.244.202.30"
				settings['proxyport'] = "8080"
				settings['mmsc'] = "http://mmsc.tele2.se"
				settings['pdns'] = "0.0.0.0"
				settings['sdns'] = "0.0.0.0"
				settings['ip'] = "0.0.0.0"
				return settings
		return False

	def reset_all_settings(self):
		self.config.reset_all_settings()


class Locker:
	def __init__(self, fn):
		self.fn = fn
		self.fd = None
		self.pid = os.getpid()
		self.failcounter = 0
	
	def lock(self):
		try:
			self.fd = os.open(self.fn, os.O_CREAT | os.O_EXCL | os.O_RDWR)
			os.write(self.fd, "%d" % self.pid)
			return 1
		except OSError:
			# we failed to lock
			self.fd = None
			self.failcounter += 1
			# after 5 unsuccessful locks we check the owner
			# is still alive
			if self.failcounter > 4:
				pid = open(self.fn, 'r').read()
				try:
					os.kill(int(pid), 0)
				except OSError, e:
					# no such process, remove the lock
					os.remove(self.fn)
			return 0
	
	def unlock(self):
		if not self.fd:
			return 0
		try:
			os.close(self.fd)
			os.remove(self.fn)
			return 1
		except OSError:
			return 0
			
	def __del__(self):
		# deconstructor, make sure lock is released
		self.unlock()

if __name__ == '__main__':
	c = fMMS_controller()