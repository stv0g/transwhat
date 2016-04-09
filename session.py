__author__ = u"Steffen Vogel"
__copyright__ = u"Copyright 2015, Steffen Vogel"
__license__ = u"GPLv3"
__maintainer__ = u"Steffen Vogel"
__email__ = u"post@steffenvogel.de"

u"""
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
import sys
import os

from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_media.mediadownloader import MediaDownloader

from Spectrum2 import protocol_pb2

from buddy import BuddyList
from threading import Timer
from group import Group
from bot import Bot
import deferred
from deferred import call
from yowsupwrapper import YowsupApp


class MsgIDs:
        def __init__(self, xmppId, waId):
                self.xmppId = xmppId
                self.waId = waId
                self.cnt = 0




class Session(YowsupApp):
	broadcast_prefix = u'\U0001F4E2 '

	def __init__(self, backend, user, legacyName, extra):
		super(Session, self).__init__()
		self.logger = logging.getLogger(self.__class__.__name__)
		self.logger.info(u"Created: %s", legacyName)

		self.backend = backend
		self.user = user
		self.legacyName = legacyName

		self.status = protocol_pb2.STATUS_NONE
		self.statusMessage = u''

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
		self.recvMsgIDs = []

		self.timer = None
		self.password = None
		self.initialized = False
		self.lastMsgId = None
		self.synced = False

		self.buddies = BuddyList(self.legacyName, self.backend, self.user, self)
		self.bot = Bot(self)

		self.imgMsgId = None
		self.imgPath = u""
		self.imgBuddy = None
		self.imgType = u""


	def __del__(self): # handleLogoutRequest
		self.logout()

	def logout(self):
		self.logger.info(u"%s logged out", self.user)
		super(Session, self).logout()
		self.loggedIn = False

	def login(self, password):
		self.logger.info(u"%s attempting login", self.user)
		self.password = password
		self.shouldBeConncted = True
		super(Session, self).login(self.legacyName, self.password)

	def updateRoomList(self):
		rooms = []
		text = []
		for room, group in self.groups.iteritems():
			rooms.append([room, group.subject])
			text.append(room.decode('utf-8') + u'@' + self.backend.spectrum_jid.decode('utf-8') + u' :' + group.subject.decode('utf-8'))

		self.logger.debug(u"Got rooms: %s", rooms)
		self.backend.handleRoomList(rooms)
		message = u"Note, you are a participant of the following groups:\n" +\
		          u'\n'.join(text) + u'\nIf you do not join them you will lose messages'
		#self.bot.send(message)

	def _updateGroups(self, response, request):
		self.logger.debug(u'Received groups list %s', str(response).decode('utf-8'))
		groups = response.getGroups()
		for group in groups:
			room = group.getId()
			owner = group.getOwner().split(u'@')[0]
			subjectOwner = group.getSubjectOwner().split(u'@')[0]
			subject = utils.softToUni(group.getSubject())

			if room in self.groups:
				oroom = self.groups[room]
				oroom.owner = owner
				oroom.subjectOwner = subjectOwner
				oroom.subject = subject
			else:
				self.groups[room] = Group(room, owner, subject, subjectOwner, self.backend, self.user)
#				self.joinRoom(self._shortenGroupId(room), self.user.split(u"@")[0])
			self.groups[room].addParticipants(group.getParticipants().keys(),
					self.buddies, self.legacyName)

			#self._addParticipantsToRoom(room, group.getParticipants())

			if room in self.groupOfflineQueue:
				while self.groupOfflineQueue[room]:
					msg = self.groupOfflineQueue[room].pop(0)
					self.backend.handleMessage(self.user, room, msg[1],
											   msg[0], u"", msg[2])
					self.logger.debug(u"Send queued group message to: %s %s %s",
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
		room = room
		if room in self.groups:
			self.logger.info(u"Joining room: %s room=%s, nick=%s",
							 self.legacyName, room, nick)

			group = self.groups[room]
			group.joined = True
			group.nick = nick
			group.participants[self.legacyName] = nick
			try:
				ownerNick = group.participants[group.subjectOwner]
			except KeyError:
				ownerNick = group.subjectOwner

			group.sendParticipantsToSpectrum(self.legacyName)
			self.backend.handleSubject(self.user, room,
									   group.subject, ownerNick)
			self.logger.debug(u"Room subject: room=%s, subject=%s",
							  room.decode('utf-8'), group.subject.decode('utf-8'))
			self.backend.handleRoomNicknameChanged(
				self.user, room, group.subject
			)
		else:
			self.logger.warn(u"Room doesn't exist: %s", room)

	def leaveRoom(self, room):
		if room in self.groups:
			self.logger.info(u"Leaving room: %s room=%s", self.legacyName, room)
			group = self.groups[room]
			group.joined = False
		else:
			self.logger.warn(u"Room doesn't exist: %s. Unable to leave.", room)

	def _lastSeen(self, number, seconds):
		self.logger.debug(u"Last seen %s at %s seconds", number, seconds)
		if seconds < 60:
			self.onPresenceAvailable(number)
		else:
			self.onPresenceUnavailable(number)
	def sendReadReceipts(self, buddy):
		for _id, _from, participant, t in self.recvMsgIDs:
			if _from.split(u'@')[0] == buddy:
				self.sendReceipt(_id, _from, 'read', participant, t)
				self.recvMsgIDs.remove((_id, _from, participant, t))
				self.logger.debug(u"Send read receipt to %s (ID: %s)", _from, _id)

	# Called by superclass
	def onAuthSuccess(self, status, kind, creation,
			expiration, props, nonce, t):
		self.logger.info(u"Auth success: %s", self.user)

		self.backend.handleConnected(self.user)
		self.backend.handleBuddyChanged(self.user, u"bot", self.bot.name,
										[u"Admin"], protocol_pb2.STATUS_ONLINE)
		# Initialisation?
		self.requestPrivacyList()
		self.requestClientConfig()
		self.requestServerProperties()
		# ?

		self.logger.debug(u'Requesting groups list')
		self.requestGroupsList(self._updateGroups)
		# self.requestBroadcastList()

		# This should handle, sync, statuses, and presence
		self.sendPresence(True)
		for func in self.loginQueue:
			func()

		if self.initialized == False:
			self.sendOfflineMessages()
			#self.bot.call(u"welcome")
			self.initialized = True

		self.loggedIn = True

	# Called by superclass
	def onAuthFailed(self, reason):
		self.logger.info(u"Auth failed: %s (%s)", self.user, reason)
		self.backend.handleDisconnected(self.user, 0, reason)
		self.password = None
		self.loggedIn = False

	# Called by superclass
	def onDisconnect(self):
		self.logger.debug(u'Disconnected')
		self.backend.handleDisconnected(self.user, 0, u'Disconnected for unknown reasons')

	# Called by superclass
	def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
		self.logger.debug(u"received receipt, sending ack: %s",
			[_id, _from, timestamp, type, participant, offline, items]
		)
		try:
			number = _from.split(u'@')[0]
			self.backend.handleMessageAck(self.user, number, self.msgIDs[_id].xmppId)
			self.msgIDs[_id].cnt = self.msgIDs[_id].cnt + 1
			if self.msgIDs[_id].cnt == 2:
				del self.msgIDs[_id]
		except KeyError:
			self.logger.error(u"Message %s not found. Unable to send ack", _id)

	# Called by superclass
	def onAck(self, _id, _class, _from, timestamp):
		self.logger.debug(u'received ack: %s', [_id, _class, _from, timestamp])

	# Called by superclass
	def onTextMessage(self, _id, _from, to, notify, timestamp, participant,
					  offline, retry, body):
		self.logger.debug(u'received TextMessage %s', [
			_id, _from, to, notify, timestamp,
			participant, offline, retry, body
		])
		buddy = _from.split(u'@')[0]
		messageContent = utils.softToUni(body)
		self.sendReceipt(_id, _from, None, participant, timestamp)
		self.recvMsgIDs.append((_id, _from, participant, timestamp))
		self.logger.info(u"Message received from %s to %s: %s (at ts=%s)",
				buddy, self.legacyName, messageContent, timestamp)
		if participant is not None: # Group message or broadcast
			partname = participant.split(u'@')[0]
			if _from.split(u'@')[1] == u'broadcast': # Broadcast message
				message = self.broadcast_prefix + messageContent
				self.sendMessageToXMPP(partname, message, timestamp)
			else: # Group message
				if notify is None:
					notify = u""
				self.sendGroupMessageToXMPP(buddy, partname, messageContent,
											timestamp, notify)
		else:
			self.sendMessageToXMPP(buddy, messageContent, timestamp)

	# Called by superclass
	def onImage(self, image):
		self.logger.debug(u'Received image message %s', str(image))
		buddy = image._from.split(u'@')[0]
		participant = image.participant
		if image.caption is None:
			image.caption = u''
		if participant is not None: # Group message
			partname = participant.split(u'@')[0]
			if image._from.split(u'@')[1] == u'broadcast': # Broadcast message
				self.sendMessageToXMPP(partname, self.broadcast_prefix, image.timestamp)
				self.sendMessageToXMPP(partname, image.url, image.timestamp)
				self.sendMessageToXMPP(partname, image.caption, image.timestamp)
			else: # Group message
				self.sendGroupMessageToXMPP(buddy, partname, image.url, image.timestamp)
				self.sendGroupMessageToXMPP(buddy, partname, image.caption, image.timestamp)
		else:
			self.sendMessageToXMPP(buddy, image.url, image.timestamp)
			self.sendMessageToXMPP(buddy, image.caption, image.timestamp)
		self.sendReceipt(image._id,	 image._from, None, image.participant, image.timestamp)
		self.recvMsgIDs.append((image._id, image._from, image.participant, image.timestamp))


	# Called by superclass
	def onAudio(self, audio):
		self.logger.debug(u'Received audio message %s', str(audio))
		buddy = audio._from.split(u'@')[0]
                participant = audio.participant
		message = audio.url
		if participant is not None: # Group message
			partname = participant.split(u'@')[0]
			if audio._from.split(u'@')[1] == u'broadcast': # Broadcast message
				self.sendMessageToXMPP(partname, self.broadcast_prefix, audio.timestamp)
				self.sendMessageToXMPP(partname, message, audio.timestamp)
			else: # Group message
				self.sendGroupMessageToXMPP(buddy, partname, message, audio.timestamp)
		else:
			self.sendMessageToXMPP(buddy, message, audio.timestamp)
		self.sendReceipt(audio._id,	 audio._from, None, audio.participant, audio.timestamp)
		self.recvMsgIDs.append((audio._id, audio._from, audio.participant, audio.timestamp))


	# Called by superclass
	def onVideo(self, video):
		self.logger.debug(u'Received video message %s', str(video))
		buddy = video._from.split(u'@')[0]
                participant = video.participant

		message = video.url
		if participant is not None: # Group message
			partname = participant.split(u'@')[0]
			if video._from.split(u'@')[1] == u'broadcast': # Broadcast message
				self.sendMessageToXMPP(partname, self.broadcast_prefix, video.timestamp)
				self.sendMessageToXMPP(partname, message, video.timestamp)
			else: # Group message
				self.sendGroupMessageToXMPP(buddy, partname, message, video.timestamp)
		else:
			self.sendMessageToXMPP(buddy, message, video.timestamp)
		self.sendReceipt(video._id,	 video._from, None, video.participant, video.timestamp)
		self.recvMsgIDs.append((video._id, video._from, video.participant, video.timestamp))


	def onLocation(self, location):
		buddy = location._from.split(u'@')[0]
		latitude = location.getLatitude()
		longitude = location.getLongitude()
		url = location.getLocationURL()
                participant = location.participant
		latlong = u'geo:' + latitude + u',' + longitude

		self.logger.debug(u"Location received from %s: %s, %s",
						  buddy, latitude, longitude)


		if participant is not None: # Group message
			partname = participant.split(u'@')[0]
			if location._from.split(u'@')[1] == u'broadcast': # Broadcast message
				self.sendMessageToXMPP(partname, self.broadcast_prefix, location.timestamp)
				if url is not None:
					self.sendMessageToXMPP(partname, url, location.timestamp)
				self.sendMessageToXMPP(partname, latlong, location.timestamp)
			else: # Group message
				if url is not None:
					self.sendGroupMessageToXMPP(buddy, partname, url, location.timestamp)
				self.sendGroupMessageToXMPP(buddy, partname, latlong, location.timestamp)
		else:
			if url is not None:
				self.sendMessageToXMPP(buddy, url, location.timestamp)
			self.sendMessageToXMPP(buddy, latlong, location.timestamp)
		self.sendReceipt(location._id, location._from, None, location.participant, location.timestamp)
		self.recvMsgIDs.append((location._id, location._from, location.participant, location.timestamp))



	# Called by superclass
	def onVCard(self, _id, _from, name, card_data, to, notify, timestamp, participant):
		self.logger.debug(u'received VCard %s', [
				_id, _from, name, card_data, to, notify, timestamp, participant
			])
		message =  u"Received VCard (not implemented yet)"
		buddy = _from.split(u"@")[0]
		if participant is not None: # Group message
			partname = participant.split(u'@')[0]
			if _from.split(u'@')[1] == u'broadcast': # Broadcast message
				message = self.broadcast_prefix + message
				self.sendMessageToXMPP(partname, message, timestamp)
			else: # Group message
				self.sendGroupMessageToXMPP(buddy, partname, message, timestamp)
		else:
			self.sendMessageToXMPP(buddy, message, timestamp)
#		self.sendMessageToXMPP(buddy, card_data)
		#self.transferFile(buddy, str(name), card_data)
		self.sendReceipt(_id, _from, None, participant, timestamp)
		self.recvMsgIDs.append((_id, _from, participant, timestamp))


	def transferFile(self, buddy, name, data):
		# Not working
		self.logger.debug(u'transfering file %s', name)
		self.backend.handleFTStart(self.user, buddy, name, len(data))
		self.backend.handleFTData(0, data)
		self.backend.handleFTFinish(self.user, buddy, name, len(data), 0)

	# Called by superclass
	def onContactTyping(self, buddy):
		self.logger.info(u"Started typing: %s", buddy)
		if buddy != u'bot':
			self.sendPresence(True)
			self.backend.handleBuddyTyping(self.user, buddy)

			if self.timer != None:
				self.timer.cancel()

	# Called by superclass
	def onContactPaused(self, buddy):
		self.logger.info(u"Paused typing: %s", buddy)
		if buddy != u'bot':
			self.backend.handleBuddyTyped(self.user, buddy)
			self.timer = Timer(3, self.backend.handleBuddyStoppedTyping,
							   (self.user, buddy)).start()

	# Called by superclass
	def onAddedToGroup(self, group):
		self.logger.debug(u"Added to group: %s", group)
		room = group.getGroupId()
		owner = group.getCreatorJid(full = False)
		subjectOwner = group.getSubjectOwnerJid(full = False)
		subject = utils.softToUni(group.getSubject())

		self.groups[room] = Group(room, owner, subject, subjectOwner, self.backend, self.user)
		self.groups[room].addParticipants(group.getParticipants, self.buddies, self.legacyName)
		self.bot.send(u"You have been added to group: %s@%s (%s)"
					  % (room, subject, self.backend.spectrum_jid))

	# Called by superclass
	def onParticipantsAddedToGroup(self, group):
		self.logger.debug(u"Participants added to group: %s", group)
		room = group.getGroupId().split(u'@')[0]
		self.groups[room].addParticipants(group.getParticipants(), self.buddies, self.legacyName)
		self.groups[room].sendParticipantsToSpectrum(self.legacyName)

	# Called by superclass
	def onSubjectChanged(self, room, subject, subjectOwner, timestamp):
		self.logger.debug(
			u"onSubjectChange(room=%s, subject=%s, subjectOwner=%s, timestamp=%s)",
			room, subject, subjectOwner, timestamp)
		try:
			group = self.groups[room]
		except KeyError:
			self.logger.error(u"Subject of non-existant group (%s) changed", group)
		else:
			group.subject = subject
			group.subjectOwner = subjectOwner
			if not group.joined:
				# We have not joined group so we should not send subject
				return
		self.backend.handleSubject(self.user, room, subject, subjectOwner)
		self.backend.handleRoomNicknameChanged(self.user, room, subject)

	# Called by superclass
	def onParticipantsRemovedFromGroup(self, room, participants):
		self.logger.debug(u"Participants removed from group: %s, %s",
				room, participants)
		self.groups[room].removeParticipants(participants)

	# Called by superclass
	def onContactStatusChanged(self, number, status):
		self.logger.debug(u"%s changed their status to %s", number, status)
		try:
			buddy = self.buddies[number]
			buddy.statusMsg = status
			self.buddies.updateSpectrum(buddy)
		except KeyError:
			self.logger.debug(u"%s not in buddy list", number)

	# Called by superclass
	def onContactPictureChanged(self, number):
		self.logger.debug(u"%s changed their profile picture", number)
		self.buddies.requestVCard(number)

	# Called by superclass
	def onContactAdded(self, number, nick):
		self.logger.debug(u"Adding new contact %s (%s)", nick, number)
		self.updateBuddy(number, nick, [])

	# Called by superclass
	def onContactRemoved(self, number):
		self.logger.debug(u"Removing contact %s", number)
		self.removeBuddy(number)

	def onContactUpdated(self, oldnumber, newnumber):
		self.logger.debug(u"Contact has changed number from %s to %s",
				oldnumber, newnumber)
		if newnumber in self.buddies:
			self.logger.warn(u"Contact %s exists, just updating", newnumber)
			self.buddies.refresh(newnumber)
		try:
			buddy = self.buddies[oldnumber]
		except KeyError:
			self.logger.warn(u"Old contact (%s) not found. Adding new contact (%s)",
				oldnumber, newnumber)
			nick = u""
		else:
			self.removeBuddy(buddy.number)
			nick = buddy.nick
		self.updateBuddy(newnumber, nick, [])

	def onPresenceReceived(self, _type, name, jid, lastseen):
		self.logger.info(u"Presence received: %s %s %s %s", _type, name, jid, lastseen)
		buddy = jid.split(u"@")[0]
		try:
			buddy = self.buddies[buddy]
		except KeyError:
			# Sometimes whatsapp send our own presence
			if buddy != self.legacyName:
				self.logger.error(u"Buddy not found: %s", buddy)
			return

		if (lastseen == str(buddy.lastseen)) and (_type == buddy.presence):
			return

		if ((lastseen != u"deny") and (lastseen != None) and (lastseen != u"none")):
			buddy.lastseen = int(lastseen)
		if (_type == None):
			buddy.lastseen = time.time()

		buddy.presence = _type

		if _type == u"unavailable":
			self.onPresenceUnavailable(buddy)
		else:
			self.onPresenceAvailable(buddy)



	def onPresenceAvailable(self, buddy):
		self.logger.info(u"Is available: %s", buddy)
		self.buddies.updateSpectrum(buddy)

	def onPresenceUnavailable(self, buddy):
		self.logger.info(u"Is unavailable: %s", buddy)
		self.buddies.updateSpectrum(buddy)

	# spectrum RequestMethods
	def sendTypingStarted(self, buddy):
		if buddy != u"bot":
			self.logger.info(u"Started typing: %s to %s", self.legacyName, buddy)
			self.sendTyping(buddy, True)
			self.sendReadReceipts(buddy)
		# If he is typing he is present
		# I really don't know where else to put this.
		# Ideally, this should be sent if the user is looking at his client
		self.sendPresence(True)

	def sendTypingStopped(self, buddy):
		if buddy != "bot":
			self.logger.info("Stopped typing: %s to %s", self.legacyName, buddy)
			self.sendTyping(buddy, False)
			self.sendReadReceipts(buddy)

	def sendImage(self, message, ID, to):
		if (".jpg" in message.lower()):
			imgType = "jpg"
		if (".webp" in message.lower()):
			imgType = "webp"

		success = deferred.Deferred()
		error = deferred.Deferred()
		self.downloadMedia(message, success.run, error.run)

		# Success
		path = success.arg(0)
		call(self.logger.info, "Success: Image downloaded to %s", path)
		pathWithExt = path.then(lambda p: p + "." + imgType)
		call(os.rename, path, pathWithExt)
		pathJpg = path.then(lambda p: p + ".jpg")
		if imgType != "jpg":
			im = call(Image.open, pathWithExt)
			call(im.save, pathJpg)
			call(os.remove, pathWithExt)
		call(self.logger.info, "Sending image to %s", to)
		waId = deferred.Deferred()
		call(super(Session, self).sendImage, to, pathJpg, onSuccess = waId.run)
		call(self.setWaId, ID, waId)
		waId.when(call, os.remove, pathJpg)
		waId.when(self.logger.info, "Image sent")

		# Error
		error.when(self.logger.info, "Download Error. Sending message as is.")
		waId = error.when(self.sendTextMessage, to, message)
		call(self.setWaId, ID, waId)

	def setWaId(self, XmppId, waId):
		self.msgIDs[waId] = MsgIDs(XmppId, waId)

	def sendMessageToWA(self, sender, message, ID, xhtml=""):
		self.logger.info("Message sent from %s to %s: %s (xhtml=%s)",
						 self.legacyName, sender, message, xhtml)

		message = message.encode("utf-8")
		self.sendReadReceipts(sender)

		if sender == "bot":
			self.bot.parse(message)
		elif "-" in sender: # group msg
			if "/" in sender: # directed at single user
				room, nick = sender.split("/")
				group = self.groups[room]
				number = None
				for othernumber, othernick in group.participants.iteritems():
					if othernick == nick:
						number = othernumber
						break
				if number is not None:
					self.logger.debug("Private message sent from %s to %s", self.legacyName, number)
					waId = self.sendTextMessage(number + u'@s.whatsapp.net', message)
					self.msgIDs[waId] = MsgIDs( ID, waId)
				else:
					self.logger.error("Attempted to send private message to non-existent user")
					self.logger.debug("%s to %s in %s", self.legacyName, nick, room)
			else:
				room = sender
				if message[0] == u'\\' and message[:1] != u'\\\\':
					self.logger.debug("Executing command %s in %s", message, room)
					self.executeCommand(message, room)
				else:
					try:
						group = self.groups[room]
						self.logger.debug("Group Message from %s to %s Groups: %s",
										 group.nick , group , self.groups)
						self.backend.handleMessage(
							self.user, room, message.decode(u'utf-8'), group.nick, xhtml=xhtml
						)
					except KeyError:
						self.logger.error(u'Group not found: %s', room)

				if (".jpg" in message.lower()) or (".webp" in message.lower()):
					self.sendImage(message, ID, room + u'@g.us')
				elif "geo:" in message.lower():
					self._sendLocation(room + "@g.us", message, ID)
				else:
					self.sendTextMessage(room + u'@g.us', message)
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
					self.sendImage(message, ID, buddy + "@s.whatsapp.net")
                                elif "geo:" in message.lower():
                                        self._sendLocation(buddy + "@s.whatsapp.net", message, ID)
                                else:
                                        waId = self.sendTextMessage(sender + u'@s.whatsapp.net', message)
                                        self.msgIDs[waId] = MsgIDs( ID, waId)

                                        self.logger.info("WA Message send to %s with ID %s", buddy, waId)
			#self.sendTextMessage(sender + u'@s.whatsapp.net', message)
	
	def executeCommand(self, command, room):
		if command == u'\\leave':
			self.logger.debug("Leaving room %s", room)
			# Leave group on whatsapp side
			self.leaveGroup(room)
			# Delete Room on spectrum side
			group = self.groups[room]
			group.leaveRoom()
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
                #with open(u'/opt/transwhat/map.jpg', 'rb') as imageFile:
                #        raw = base64.b64encode(imageFile.read())
                latitude,longitude = message.split(u':')[1].split(',')
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

	def sendGroupMessageToXMPP(self, room, number, messageContent, timestamp = u"", defaultname = u""):
		if timestamp:
			timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

		if self.initialized == False:
			self.logger.debug("Group message queued from %s to %s: %s",
							  number, room, messageContent)

			if room not in self.groupOfflineQueue:
				self.groupOfflineQueue[room] = [ ]

			self.groupOfflineQueue[room].append(
				(number, messageContent, timestamp)
			)
		else:
			self.logger.debug("Group message sent from %s to %s: %s",
							  number, room, messageContent)
			try:
				group = self.groups[room]
				# Update nickname
				try:
					if defaultname != "" and group.participants[number] == number:
						group.changeNick(number, defaultname)
					if self.buddies[number].nick != "":
						group.changeNick(number, self.buddies[number].nick)
				except KeyError:
					pass
				nick = group.participants[number]
				if group.joined:
					self.backend.handleMessage(self.user, room, messageContent,
							nick, "", timestamp)
				else:
					self.bot.send("You have received a message in group: %s@%s"
							% (room, self.backend.spectrum_jid))
					self.bot.send("Join the group in order to reply")
					self.bot.send("%s: %s" % (nick, messageContent))
			except KeyError:
				self.logger.warn("Group is not in group list")
				self.backend.handleMessage(self.user, room,
						messageContent, number, "", timestamp)


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
			self.setStatus(statusMessage.encode(u'utf-8'))
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
		self.buddies.requestVCard(buddy, ID)

	def createThumb(self, size=100, raw=False):
                img = Image.open(self.imgPath)
                width, height = img.size
                img_thumbnail = self.imgPath + u'_thumbnail'

                if width > height:
                        nheight = float(height) / width * size
                        nwidth = size
                else:
                        nwidth = float(width) / height * size
                        nheight = size

                img.thumbnail((nwidth, nheight), Image.ANTIALIAS)
                img.save(img_thumbnail, u'JPEG')

                with open(img_thumbnail, 'rb') as imageFile:
                        raw = base64.b64encode(imageFile.read())

                return raw

	# Not used
	def onLocationReceived(self, messageId, jid, name, preview, latitude, longitude, receiptRequested, isBroadcast):
		buddy = jid.split(u"@")[0]
		self.logger.info(u"Location received from %s: %s, %s", buddy, latitude, longitude)

		url = u"http://maps.google.de?%s" % urllib.urlencode({ u"q": u"%s %s" % (latitude, longitude) })
		self.sendMessageToXMPP(buddy, utils.shorten(url))
		if receiptRequested: self.call(u"message_ack", (jid, messageId))


	def onGroupSubjectReceived(self, messageId, gjid, jid, subject, timestamp, receiptRequested):
		room = gjid.split(u"@")[0]
		buddy = jid.split(u"@")[0]

		self.backend.handleSubject(self.user, room, subject, buddy)
		if receiptRequested: self.call(u"subject_ack", (gjid, messageId))

	# Yowsup Notifications
	def onGroupParticipantRemoved(self, gjid, jid, author, timestamp, messageId, receiptRequested):
		room = gjid.split(u"@")[0]
		buddy = jid.split(u"@")[0]

		self.logger.info(u"Removed %s from room %s", buddy, room)

		self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_NONE) # TODO
		if receiptRequested: self.call(u"notification_ack", (gjid, messageId))

	def onContactProfilePictureUpdated(self, jid, timestamp, messageId, pictureId, receiptRequested):
		# TODO
		if receiptRequested: self.call(u"notification_ack", (jid, messageId))

	def onGroupPictureUpdated(self, jid, author, timestamp, messageId, pictureId, receiptRequested):
		# TODO
		if receiptRequested: self.call(u"notification_ack", (jid, messageId))



