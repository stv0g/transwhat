__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2013, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"
__status__ = "Prototype"

"""
 This file is part of transWhat

 transWhat is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 any later version.

 transwhat is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with transWhat. If not, see <http://www.gnu.org/licenses/>.
"""

import utils
import logging
import urllib
import time

from PIL import Image
import MySQLdb
import sys
import os

from yowsup.common.tools import TimeTools
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_media.mediadownloader import MediaDownloader

from Spectrum2 import protocol_pb2

from buddy import BuddyList
from threading import Timer
from group import Group
from bot import Bot
from constants import *
from yowsupwrapper import YowsupApp


class MsgIDs:
        def __init__(self, xmppId, waId):
                self.xmppId = xmppId
                self.waId = waId
                self.cnt = 0




class Session(YowsupApp):

	def __init__(self, backend, user, legacyName, extra, db):
		super(Session, self).__init__()
		self.logger = logging.getLogger(self.__class__.__name__)
		self.logger.info("Created: %s", legacyName)

		#self.db = db
		self.db = MySQLdb.connect(DB_HOST, DB_USER, DB_PASS, DB_TABLE)

		self.backend = backend
		self.user = user
		self.legacyName = legacyName

		self.status = protocol_pb2.STATUS_NONE
		self.statusMessage = ''

		self.groups = {}
		self.gotGroupList = False
		# Functions to exectute when logged in via yowsup
		self.loginQueue = []
		self.joinRoomQueue = []
		self.presenceRequested = []
		self.offlineQueue = []
		self.msgIDs = { }
		self.groupOfflineQueue = { }
		self.loggedIn = False

		self.timer = None
		self.password = None
		self.initialized = False
		self.lastMsgId = None
		self.synced = False

		self.buddies = BuddyList(self.legacyName, self.backend, self.user, self)
		self.bot = Bot(self)

		self.imgMsgId = None
		self.imgPath = ""
		self.imgBuddy = None
		self.imgType = ""


	def __del__(self): # handleLogoutRequest
		self.logout()

	def logout(self):
		self.logger.info("%s logged out", self.user)
		super(Session, self).logout()
		self.loggedIn = False

	def login(self, password):
		self.logger.info("%s attempting login", self.user)
		self.password = password
		self.shouldBeConncted = True
		super(Session, self).login(self.legacyName, self.password)

	def _shortenGroupId(self, gid):
		# FIXME: might have problems if number begins with 0
		return gid
#		return '-'.join(hex(int(s))[2:] for s in gid.split('-'))

	def _lengthenGroupId(self, gid):
		return gid
		# FIXME: might have problems if number begins with 0
#		return '-'.join(str(int(s, 16)) for s in gid.split('-'))

	def updateRoomList(self):
		rooms = []
		text = []
		for room, group in self.groups.iteritems():
			rooms.append([self._shortenGroupId(room), group.subject])
			text.append(self._shortenGroupId(room) + '@' + self.backend.spectrum_jid + ' :' + group.subject)

		self.logger.debug("Got rooms: %s", rooms)
		self.backend.handleRoomList(rooms)
		message = "Note, you are a participant of the following groups:\n" +\
		          '\n'.join(text) + '\nIf you do not join them you will lose messages'
		#self.bot.send(message)

	def _updateGroups(self, response, request):
		self.logger.debug('Received groups list %s', response)
		groups = response.getGroups()
		for group in groups:
			room = group.getId()
			owner = group.getOwner().split('@')[0]
			subjectOwner = group.getSubjectOwner().split('@')[0]
			subject = utils.softToUni(group.getSubject())

			if room in self.groups:
				oroom = self.groups[room]
				oroom.owner = owner
				oroom.subjectOwner = subjectOwner
				oroom.subject = subject
			else:
				self.groups[room] = Group(room, owner, subject, subjectOwner)
#				self.joinRoom(self._shortenGroupId(room), self.user.split("@")[0])
			self.groups[room].participants = group.getParticipants().keys()

			#self._addParticipantsToRoom(room, group.getParticipants())

			if room in self.groupOfflineQueue:
				while self.groupOfflineQueue[room]:
					msg = self.groupOfflineQueue[room].pop(0)
					self.backend.handleMessage(self.user, room, msg[1],
											   msg[0], "", msg[2])
					self.logger.debug("Send queued group message to: %s %s %s",
									  msg[0],msg[1], msg[2])
		self.gotGroupList = True
		for room, nick in self.joinRoomQueue:
			self.joinRoom(room, nick)
		self.joinRoomQueue = []
		self.updateRoomList()

	def joinRoom(self, room, nick):
		if not self.gotGroupList:
			self.joinRoomQueue.append((room, nick))
			return
		room = self._lengthenGroupId(room)
		if room in self.groups:
			self.logger.info("Joining room: %s room=%s, nick=%s",
							 self.legacyName, room, nick)

			group = self.groups[room]
			group.nick = nick
			try:
				ownerNick = self.buddies[group.subjectOwner].nick
			except KeyError:
				ownerNick = group.subjectOwner

			self._refreshParticipants(room)
			self.backend.handleSubject(self.user, self._shortenGroupId(room),
									   group.subject, ownerNick)
			self.logger.debug("Room subject: room=%s, subject=%s",
							  room, group.subject)
			self.backend.handleRoomNicknameChanged(
				self.user, self._shortenGroupId(room), group.subject
			)
			group.joined = True
		else:
			self.logger.warn("Room doesn't exist: %s", room)

	def leaveRoom(self, room):
		if room in self.groups:
			self.logger.info("Leaving room: %s room=%s", self.legacyName, room)
			group = self.groups[room]
			group.joined = False
		else:
			self.logger.warn("Room doesn't exist: %s. Unable to leave.", room)

	def _refreshParticipants(self, room):
		group = self.groups[room]
		for jid in group.participants:
			buddy = jid.split("@")[0]
			self.logger.info("Added %s to room %s", buddy, room)
			try:
				nick = self.buddies[buddy].nick
			except KeyError:
				nick = buddy
			if nick == "":
				nick = buddy

			if buddy == group.owner:
				flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
			else:
				flags = protocol_pb2.PARTICIPANT_FLAG_NONE
			if buddy == self.legacyName:
				nick = group.nick
				flags = flags | protocol_pb2.PARTICIPANT_FLAG_ME
			self.backend.handleParticipantChanged(
				self.user, nick, self._shortenGroupId(room), flags,
				protocol_pb2.STATUS_ONLINE, buddy)

	def _lastSeen(self, number, seconds):
		self.logger.debug("Last seen %s at %s seconds" % (number, str(seconds)))
		if seconds < 60:
			self.onPresenceAvailable(number)
		else:
			self.onPresenceUnavailable(number)

	# Called by superclass
	def onAuthSuccess(self, status, kind, creation,
			expiration, props, nonce, t):
		self.logger.info("Auth success: %s", self.user)

		self.backend.handleConnected(self.user)
		self.backend.handleBuddyChanged(self.user, "bot", self.bot.name,
										["Admin"], protocol_pb2.STATUS_ONLINE)
		if self.initialized == False:
			self.sendOfflineMessages()
			#self.bot.call("welcome")
			self.initialized = True
		self.sendPresence(True)
		for func in self.loginQueue:
			func()

		self.logger.debug('Requesting groups list')
		self.requestGroupsList(self._updateGroups)
		self.loggedIn = True

	# Called by superclass
	def onAuthFailed(self, reason):
		self.logger.info("Auth failed: %s (%s)", self.user, reason)
		self.backend.handleDisconnected(self.user, 0, reason)
		self.password = None
		self.loggedIn = False

	# Called by superclass
	def onDisconnect(self):
		self.logger.debug('Disconnected')
		self.backend.handleDisconnected(self.user, 0, 'Disconnected for unknown reasons')

	# Called by superclass
	def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
		self.logger.debug("received receipt, sending ack: " +
				' '.join(map(str, [_id, _from, timestamp,
					type, participant, offline, items]))
		)
		try:
			buddy = self.buddies[_from.split('@')[0]]
			#self.backend.handleBuddyChanged(self.user, buddy.number.number,
			#		buddy.nick, buddy.groups, protocol_pb2.STATUS_ONLINE)
			self.backend.handleMessageAck(self.user, buddy.number, self.msgIDs[_id].xmppId)
                        self.msgIDs[_id].cnt = self.msgIDs[_id].cnt +1
                        if self.msgIDs[_id].cnt == 2:
                                del self.msgIDs[_id]

		except KeyError:
			pass

	# Called by superclass
	def onAck(self, _id, _class, _from, timestamp):
		self.logger.debug('received ack ' + 
				' '.join(map(str, [_id, _class, _from,timestamp,]))
		)

	# Called by superclass
	def onTextMessage(self, _id, _from, to, notify, timestamp, participant,
					  offline, retry, body):
		self.logger.debug('received TextMessage' +
			' '.join(map(str, [
				_id, _from, to, notify, timestamp,
				participant, offline, retry, body
			]))
		)
		buddy = _from.split('@')[0]
		messageContent = utils.softToUni(body)
		self.sendReceipt(_id, _from, None, participant)
		self.logger.info("Message received from %s to %s: %s (at ts=%s)",
				buddy, self.legacyName, messageContent, timestamp)
		if participant is not None: # Group message
			partname = participant.split('@')[0]
			try:
				part = self.buddies[partname]
				if part.nick == "":
					part.nick = notify
					self.backend.handleParticipantChanged(
						self.user, partname, self._shortenGroupId(buddy),
						protocol_pb2.PARTICIPANT_FLAG_NONE,
						protocol_pb2.STATUS_ONLINE, "", part.nick
					) # TODO
			except KeyError:
				self.updateBuddy(partname, notify, [])
			self.sendGroupMessageToXMPP(buddy, partname, messageContent,
										timestamp)
		else:
			self.sendMessageToXMPP(buddy, messageContent, timestamp)
		# isBroadcast always returns false, I'm not sure how to get a broadcast
		# message.
		#if messageEntity.isBroadcast():
		#	self.logger.info("Broadcast received from %s to %s: %s (at ts=%s)",\
		#			buddy, self.legacyName, messageContent, timestamp)
		#	messageContent = "[Broadcast] " + messageContent

	# Called by superclass
	def onImage(self, image):
		self.logger.debug('Received image message %s', str(image))
		buddy = image._from.split('@')[0]
		participant = image.participant
		if image.caption is None:
                        image.caption = ''
		message = image.url + ' ' + image.caption
		if participant is not None: # Group message
                        partname = participant.split('@')[0]
                        self.sendGroupMessageToXMPP(buddy, partname, message, image.timestamp)
                else:

			self.sendMessageToXMPP(buddy, message, image.timestamp)
		self.sendReceipt(image._id,	 image._from, None, image.participant)

	# Called by superclass
	def onAudio(self, audio):
		self.logger.debug('Received audio message %s', str(audio))
		buddy = audio._from.split('@')[0]
                participant = audio.participant
		message = audio.url
		if participant is not None: # Group message
                        partname = participant.split('@')[0]
                        self.sendGroupMessageToXMPP(buddy, partname, message, audio.timestamp)
                else:

			self.sendMessageToXMPP(buddy, message, audio.timestamp)
		self.sendReceipt(audio._id,	 audio._from, None, audio.participant)

	# Called by superclass
	def onVideo(self, video):
		self.logger.debug('Received video message %s', str(video))
		buddy = video._from.split('@')[0]
                participant = video.participant

		message = video.url
		if participant is not None: # Group message
                        partname = participant.split('@')[0]
                        self.sendGroupMessageToXMPP(buddy, partname, message, video.timestamp)
                else:

			self.sendMessageToXMPP(buddy, message, video.timestamp)
		self.sendReceipt(video._id,	 video._from, None, video.participant)

	def onLocation(self, location):
		buddy = location._from.split('@')[0]
		latitude = location.getLatitude()
		longitude = location.getLongitude()
		url = location.getLocationUrl()
                participant = location.participant

		self.logger.debug("Location received from %s: %s, %s",
						  buddy, latitude, longitude)

		if participant is not None: # Group message
                        partname = participant.split('@')[0]
                        self.sendGroupMessageToXMPP(buddy, partname, url, location.timestamp)
			self.sendGroupMessageToXMPP(buddy, partname, 'geo:' + latitude + ',' + longitude,
                                                           location.timestamp)
                else:

			self.sendMessageToXMPP(buddy, url, location.timestamp)
			self.sendMessageToXMPP(buddy, 'geo:' + latitude + ',' + longitude,
							   location.timestamp)
                self.sendReceipt(location._id, location._from, None, location.participant, location.timestamp)


	# Called by superclass
	def onVCard(self, _id, _from, name, card_data, to, notify, timestamp, participant):
		self.logger.debug('received VCard' +
			' '.join(map(str, [
				_id, _from, name, card_data, to, notify, timestamp, participant
			]))
		)
		buddy = _from.split("@")[0]
		if participant is not None: # Group message
                        partname = participant.split('@')[0]
                        self.sendGroupMessageToXMPP(buddy, partname, "Received VCard (not implemented yet)", timestamp)
                else:

			self.sendMessageToXMPP(buddy, "Received VCard (not implemented yet)")
#		self.sendMessageToXMPP(buddy, card_data)
		#self.transferFile(buddy, str(name), card_data)
		self.sendReceipt(_id, _from, None, participant)

	def transferFile(self, buddy, name, data):
		# Not working
		self.logger.debug('transfering file %s', name)
		self.backend.handleFTStart(self.user, buddy, name, len(data))
		self.backend.handleFTData(0, data)
		self.backend.handleFTFinish(self.user, buddy, name, len(data), 0)

	# Called by superclass
	def onContactTyping(self, buddy):
		self.logger.info("Started typing: %s", buddy)
		if buddy != 'bot':
			self.sendPresence(True)
			self.backend.handleBuddyTyping(self.user, buddy)

			if self.timer != None:
				self.timer.cancel()

	# Called by superclass
	def onContactPaused(self, buddy):
		self.logger.info("Paused typing: %s", buddy)
		if buddy != 'bot':
			self.backend.handleBuddyTyped(self.user, buddy)
			self.timer = Timer(3, self.backend.handleBuddyStoppedTyping,
							   (self.user, buddy)).start()

	# Called by superclass
	def onAddedToGroup(self, group):
		self.logger.debug("Added to group: %s", group)
		room = group.getGroupId()
		owner = group.getCreatorJid(full = False)
		subjectOwner = group.getSubjectOwnerJid(full = False)
		subject = utils.softToUni(group.getSubject())

		self.groups[room] = Group(room, owner, subject, subjectOwner)
		self.groups[room].participants = group.getParticipants().keys()
#		self.joinRoom(self._shortenGroupId(room), self.user.split("@")[0])

		#self._addParticipantsToRoom(room, group.getParticipants())
		self.bot.send("You have been added to group: %s@%s (%s)"
					  % (self._shortenGroupId(room), subject, self.backend.spectrum_jid))

	# Called by superclass
	def onParticipantsAddedToGroup(self, group):
		self.logger.debug("Participants added to group: %s", group)
		room = group.getGroupId().split('@')[0]
		self.groups[room].participants.extend(group.getParticipants())
		self._refreshParticipants(room)

	# Called by superclass
	def onParticipantsRemovedFromGroup(self, room, participants):
		self.logger.debug("Participants removed from group: %s, %s",
				room, participants)
		group = self.groups[room]
		for jid in participants:
			group.participants.remove(jid)
			buddy = jid.split("@")[0]
			try:
				nick = self.buddies[buddy].nick
			except KeyError:
				nick = buddy
			if nick == "":
				nick = buddy
			if buddy == self.legacyName:
				nick = group.nick
			flags = protocol_pb2.PARTICIPANT_FLAG_NONE
			self.backend.handleParticipantChanged(
					self.user, nick, self._shortenGroupId(room), flags,
					protocol_pb2.STATUS_NONE, buddy)

	def onPresenceReceived(self, _type, name, jid, lastseen):
		self.logger.info("Presence received: %s %s %s %s", _type, name, jid, lastseen)
		buddy = jid.split("@")[0]
                try:
                        buddy = self.buddies[buddy]
		except KeyError:
                        self.logger.error("Buddy not found: %s", buddy)
			return

		if (lastseen == str(buddy.lastseen)) and (_type == buddy.presence):
			return

		if ((lastseen != "deny") and (lastseen != None) and (lastseen != "none")): 
			buddy.lastseen = int(lastseen)
		if (_type == None):
			buddy.lastseen = time.time()

		buddy.presence = _type

		timestamp = time.localtime(buddy.lastseen)
                statusmsg = buddy.statusMsg + time.strftime("\n Last seen: %a, %d %b %Y %H:%M:%S", timestamp)

		if _type == "unavailable":
			self.onPresenceUnavailable(buddy, statusmsg)
		else:
			self.onPresenceAvailable(buddy, statusmsg)



	def onPresenceAvailable(self, buddy, statusmsg):
		self.logger.info("Is available: %s", buddy)
		self.backend.handleBuddyChanged(self.user, buddy.number,
				buddy.nick, buddy.groups, protocol_pb2.STATUS_ONLINE, statusmsg, buddy.image_hash)

	def onPresenceUnavailable(self, buddy, statusmsg):
		self.logger.info("Is unavailable: %s", buddy)
		self.backend.handleBuddyChanged(self.user, buddy.number,
				buddy.nick, buddy.groups, protocol_pb2.STATUS_AWAY, statusmsg, buddy.image_hash)

	# spectrum RequestMethods
	def sendTypingStarted(self, buddy):
		if buddy != "bot":
			self.logger.info("Started typing: %s to %s", self.legacyName, buddy)
			self.sendTyping(buddy, True)
		# If he is typing he is present
		# I really don't know where else to put this.
		# Ideally, this should be sent if the user is looking at his client
		self.sendPresence(True)

	def sendTypingStopped(self, buddy):
		if buddy != "bot":
			self.logger.info("Stopped typing: %s to %s", self.legacyName, buddy)
			self.sendTyping(buddy, False)

	def sendMessageToWA(self, sender, message, ID):
		self.logger.info("Message sent from %s to %s: %s",
						 self.legacyName, sender, message)

		message = message.encode("utf-8")
		# FIXME: Fragile, should pass this in to onDlerror
		self.dlerror_message = message
		self.dlerror_sender = sender
		self.dlerror_ID = ID
		# End Fragile

		if sender == "bot":
			self.bot.parse(message)
		elif "-" in sender: # group msg
			if "/" in sender: # directed at single user
				room, nick = sender.split("/")
				for buddy, buddy3 in self.buddies.iteritems():
						self.logger.info("Group buddy=%s nick=%s", buddy,
										 buddy3.nick)
						if buddy3.nick == nick:
							nick = buddy
				waId = self.sendTextMessage(nick + '@s.whatsapp.net', message)
				self.msgIDs[waId] = MsgIDs( ID, waId)
			else:
				room = sender
				if message[0] == '\\' and message[:1] != '\\\\':
					self.logger.debug("Executing command %s in %s", message, room)
					self.executeCommand(message, room)
				else:
					try:
						group = self.groups[self._lengthenGroupId(room)]
						self.logger.debug("Group Message from %s to %s Groups: %s",
										 group.nick , group , self.groups)
						self.backend.handleMessage(
							self.user, room, message.decode('utf-8'), group.nick
						)
					except KeyError:
						self.logger.error('Group not found: %s', room)
				
				if (".jpg" in message.lower()) or (".webp" in message.lower()):
                                        if (".jpg" in message.lower()):
                                                self.imgType = "jpg"
                                        if (".webp" in message.lower()):
                                                self.imgType = "webp"
                                        self.imgMsgId = ID
                                        self.imgBuddy = room + "@g.us"


                                        downloader = MediaDownloader(self.onDlsuccess, self.onDlerror)
                                        downloader.download(message)
                                        #self.imgMsgId = ID
                                        #self.imgBuddy = room + "@g.us"
                                elif "geo:" in message.lower():
                                        self._sendLocation(room + "@g.us", message, ID)

                                else:

                                        self.sendTextMessage(self._lengthenGroupId(room) + '@g.us', message)
		else: # private msg
			buddy = sender
#			if message == "\\lastseen":
#				self.call("presence_request", buddy = (buddy + "@s.whatsapp.net",))
#			else:
			if message.split(" ").pop(0) == "\\lastseen":
                                self.presenceRequested.append(buddy)
                                #self.call("presence_request", (buddy + "@s.whatsapp.net",))
                                self._requestLastSeen(buddy)
                        elif message.split(" ").pop(0) == "\\gpp":
                                self.logger.info("Get Profile Picture! ")
                                self.sendMessageToXMPP(buddy, "Fetching Profile Picture")
                                #self.call("contact_getProfilePicture", (buddy + "@s.whatsapp.net",))
                                self.requestVCard(buddy)
                        else:
                                if (".jpg" in message.lower()) or (".webp" in message.lower()):
                                        #waId = self.call("message_imageSend", (buddy + "@s.whatsapp.net", message, None, 0, None))
                                        #waId = self.call("message_send", (buddy + "@s.whatsapp.net", message))
                                        if (".jpg" in message.lower()):
                                                self.imgType = "jpg"
                                        if (".webp" in message.lower()):
                                                self.imgType = "webp"
                                        self.imgMsgId = ID
                                        self.imgBuddy = buddy + "@s.whatsapp.net"

					downloader = MediaDownloader(self.onDlsuccess, self.onDlerror)
                                        downloader.download(message)
                                        #self.imgMsgId = ID
                                        #self.imgBuddy = buddy + "@s.whatsapp.net"
                                elif "geo:" in message.lower():
                                        self._sendLocation(buddy + "@s.whatsapp.net", message, ID)
                                else:
                                        waId = self.sendTextMessage(sender + '@s.whatsapp.net', message)
                                        self.msgIDs[waId] = MsgIDs( ID, waId)

                                        self.logger.info("WA Message send to %s with ID %s", buddy, waId)
			#self.sendTextMessage(sender + '@s.whatsapp.net', message)
	
	def executeCommand(self, command, room):
		if command == '\\leave':
			self.logger.debug("Leaving room %s", room)
			# Leave group on whatsapp side
			self.leaveGroup(room)
			# Delete Room on spectrum side
			group = self.groups[room]
			for jid in group.participants:
				buddy = jid.split("@")[0]
				try:
					nick = self.buddies[buddy].nick
				except KeyError:
					nick = buddy
				if nick == "":
					nick = buddy
				if buddy == self.legacyName:
					nick = group.nick
				flags = protocol_pb2.PARTICIPANT_FLAG_ROOM_NOT_FOUND
				self.backend.handleParticipantChanged(
						self.user, nick, self._shortenGroupId(room), flags,
						protocol_pb2.STATUS_NONE, buddy)
			del self.groups[room]

	def _requestLastSeen(self, buddy):
		
            	def onSuccess(buddy, lastseen):
			timestamp = time.localtime(time.localtime()-lastseen)
                        timestring = time.strftime("%a, %d %b %Y %H:%M:%S", timestamp)
                        self.sendMessageToXMPP(buddy, "%s (%s) %s" % (timestring, utils.ago(lastseen),str(lastseen)))
            	def onError(errorIqEntity, originalIqEntity):
                	self.sendMessageToXMPP(errorIqEntity.getFrom(), "LastSeen Error")

		self.requestLastSeen(buddy, onSuccess, onError)

	def _sendLocation(self, buddy, message, ID):
                #with open('/opt/transwhat/map.jpg', 'rb') as imageFile:
                #        raw = base64.b64encode(imageFile.read())
                latitude,longitude = message.split(':')[1].split(',')
                waId = self.sendLocation(buddy, float(latitude), float(longitude))
                self.msgIDs[waId] = MsgIDs( ID, waId)
                self.logger.info("WA Location Message send to %s with ID %s", buddy, waId)



	def sendMessageToXMPP(self, buddy, messageContent, timestamp = "", nickname = ""):
		if timestamp:
			timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

		if self.initialized == False:
			self.logger.debug("Message queued from %s to %s: %s",
					buddy, self.legacyName, messageContent)
			self.offlineQueue.append((buddy, messageContent, timestamp))
		else:
			self.logger.debug("Message sent from %s to %s: %s", buddy,
					self.legacyName, messageContent)
			self.backend.handleMessage(self.user, buddy, messageContent, "",
					"", timestamp)

	def sendGroupMessageToXMPP(self, room, buddy, messageContent, timestamp = ""):
		# self._refreshParticipants(room)
		try:
			nick = self.buddies[buddy].nick
		except KeyError:
			nick = buddy
		if nick == "":
			nick = buddy

		if timestamp:
			timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

		if self.initialized == False:
			self.logger.debug("Group message queued from %s to %s: %s",
							  buddy, room, messageContent)

			if room not in self.groupOfflineQueue:
				self.groupOfflineQueue[room] = [ ]

			self.groupOfflineQueue[room].append(
				(buddy, messageContent, timestamp)
			)
		else:
			self.logger.debug("Group message sent from %s (%s) to %s: %s",
							  buddy, nick, room, messageContent)
			try:
				group = self.groups[room]
				if group.joined:
					self.backend.handleMessage(self.user,room, messageContent,
							nick, "", timestamp)
				else:
					self.bot.send("You have received a message in group: %s@%s"
							% (room, self.backend.spectrum_jid))
					self.bot.send("Join the group in order to reply")
					self.bot.send("%s: %s" % (nick, messageContent))
			except KeyError:
				self.logger.warn("Group is not in group list")
				self.backend.handleMessage(self.user, self._shortenGroupId(room),
						messageContent, nick, "", timestamp)


	def changeStatus(self, status):
		if status != self.status:
			self.logger.info("Status changed: %s", status)
			self.status = status

			if status == protocol_pb2.STATUS_ONLINE \
					or status == protocol_pb2.STATUS_FFC:
				self.sendPresence(True)
			else:
				self.sendPresence(False)

	def changeStatusMessage(self, statusMessage):
		if (statusMessage != self.statusMessage) or (self.initialized == False):
			self.statusMessage = statusMessage
			self.setStatus(statusMessage.encode('utf-8'))
			self.logger.info("Status message changed: %s", statusMessage)

			#if self.initialized == False:
			#	self.sendOfflineMessages()
			#	self.bot.call("welcome")
			#	self.initialized = True

	def sendOfflineMessages(self):
		# Flush Queues
		while self.offlineQueue:
			msg = self.offlineQueue.pop(0)
			self.backend.handleMessage(self.user, msg[0], msg[1], "", "", msg[2])

	# Called when user logs in to initialize the roster
	def loadBuddies(self, buddies):
		self.buddies.load(buddies)

	# also for adding a new buddy
	def updateBuddy(self, buddy, nick, groups, image_hash = None):
		if buddy != "bot":
			self.buddies.update(buddy, nick, groups, image_hash)

	def removeBuddy(self, buddy):
		if buddy != "bot":
			self.logger.info("Buddy removed: %s", buddy)
			self.buddies.remove(buddy)

	def requestVCard(self, buddy, ID=None):
		def onSuccess(response, request):
			self.logger.debug('Sending VCard (%s) with image id %s',
					ID, response.pictureId)
			image_hash = utils.sha1hash(response.pictureData)
			self.logger.debug('Image hash is %s', image_hash)
			if ID != None:
				self.backend.handleVCard(self.user, ID, buddy, "", "", response.pictureData)
			obuddy = self.buddies[buddy]
			self.updateBuddy(buddy, obuddy.nick, obuddy.groups, image_hash)

		self.logger.debug('Requesting profile picture of %s', buddy)
		self.requestProfilePicture(buddy, onSuccess = onSuccess)

	def onDlsuccess(self, path):
                self.logger.info("Success: Image downloaded to %s", path)
                os.rename(path, path+"."+self.imgType)
                if self.imgType != "jpg":
                        im = Image.open(path+"."+self.imgType)
                        im.save(path+".jpg")
                self.imgPath = path+".jpg"
                statinfo = os.stat(self.imgPath)
                name=os.path.basename(self.imgPath)
		self.logger.info("Buddy %s",self.imgBuddy)
		self.image_send(self.imgBuddy, self.imgPath)

                #self.logger.info("Sending picture %s of size %s with name %s",self.imgPath, statinfo.st_size, name)
                #mtype = "image"

                #sha1 = hashlib.sha256()
                #fp = open(self.imgPath, 'rb')
                #try:
                #        sha1.update(fp.read())
                #        hsh = base64.b64encode(sha1.digest())
                #        self.call("media_requestUpload", (hsh, mtype, os.path.getsize(self.imgPath)))
                #finally:
                #        fp.close()


        def onDlerror(self):
                self.logger.info("Download Error. Sending message as is.")
		waId = self.sendTextMessage(self.dlerror_sender + '@s.whatsapp.net', self.dlerror_message)
		self.msgIDs[waId] = MsgIDs(self.dlerror_ID, waId)


	def _doSendImage(self, filePath, url, to, ip = None, caption = None):
		waId = self.doSendImage(filePath, url, to, ip, caption)
		self.msgIDs[waId] = MsgIDs(self.imgMsgId, waId)

	def _doSendAudio(self, filePath, url, to, ip = None, caption = None):
                waId = self.doSendAudio(filePath, url, to, ip, caption)
                self.msgIDs[waId] = MsgIDs(self.imgMsgId, waId)



   
	def createThumb(self, size=100, raw=False):
                img = Image.open(self.imgPath)
                width, height = img.size
                img_thumbnail = self.imgPath + '_thumbnail'

                if width > height:
                        nheight = float(height) / width * size
                        nwidth = size
                else:
                        nwidth = float(width) / height * size
                        nheight = size

                img.thumbnail((nwidth, nheight), Image.ANTIALIAS)
                img.save(img_thumbnail, 'JPEG')

                with open(img_thumbnail, 'rb') as imageFile:
                        raw = base64.b64encode(imageFile.read())

                return raw

	# Not used
	def onLocationReceived(self, messageId, jid, name, preview, latitude, longitude, receiptRequested, isBroadcast):
		buddy = jid.split("@")[0]
		self.logger.info("Location received from %s: %s, %s", buddy, latitude, longitude)

		url = "http://maps.google.de?%s" % urllib.urlencode({ "q": "%s %s" % (latitude, longitude) })
		self.sendMessageToXMPP(buddy, utils.shorten(url))
		if receiptRequested: self.call("message_ack", (jid, messageId))


	def onGroupSubjectReceived(self, messageId, gjid, jid, subject, timestamp, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		self.backend.handleSubject(self.user, room, subject, buddy)
		if receiptRequested: self.call("subject_ack", (gjid, messageId))

	# Yowsup Notifications
	def onGroupParticipantRemoved(self, gjid, jid, author, timestamp, messageId, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		self.logger.info("Removed %s from room %s", buddy, room)

		self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_NONE) # TODO
		if receiptRequested: self.call("notification_ack", (gjid, messageId))

	def onContactProfilePictureUpdated(self, jid, timestamp, messageId, pictureId, receiptRequested):
		# TODO
		if receiptRequested: self.call("notification_ack", (jid, messageId))

	def onGroupPictureUpdated(self, jid, author, timestamp, messageId, pictureId, receiptRequested):
		# TODO
		if receiptRequested: self.call("notification_ack", (jid, messageId))



