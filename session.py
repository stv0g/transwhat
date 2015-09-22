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

from Spectrum2 import protocol_pb2

from buddy import BuddyList
from threading import Timer
from group import Group
from bot import Bot
from constants import *
from yowsupwrapper import YowsupApp

class Session(YowsupApp):

	def __init__(self, backend, user, legacyName, extra, db):
		super(Session, self).__init__()
		self.logger = logging.getLogger(self.__class__.__name__)
		self.logger.info("Created: %s", legacyName)

		self.db = db
		self.backend = backend
		self.user = user
		self.legacyName = legacyName

		self.status = protocol_pb2.STATUS_NONE
		self.statusMessage = ''

		self.groups = {}
		self.presenceRequested = []
		self.offlineQueue = []
		self.groupOfflineQueue = { }
		self.shouldBeConnected = False

		self.timer = None
		self.password = None
		self.initialized = False
		self.synced = False

		self.buddies = BuddyList(self.legacyName, self.db)
		self.bot = Bot(self)

	def __del__(self): # handleLogoutRequest
		self.logout()

	def logout(self):
		self.logger.info("%s logged out", self.user)
		super(Session, self).logout()

	def login(self, password):
		self.logger.info("%s attempting login", self.user)
		self.password = password
		self.shouldBeConncted = True
		super(Session, self).login(self.legacyName, self.password)

	def _shortenGroupId(self, gid):
		# FIXME: will have problems if number begins with 0
		return '-'.join(hex(int(s))[2:] for s in gid.split('-'))
	
	def _lengthenGroupId(self, gid):
		# FIXME: will have problems if number begins with 0
		return '-'.join(str(int(s, 16)) for s in gid.split('-'))

	def updateRoomList(self):
		rooms = []
		for room, group in self.groups.iteritems():
			rooms.append([self._shortenGroupId(room), group.subject])

		self.logger.debug("Got rooms: %s", rooms)
		self.backend.handleRoomList(rooms)

	def updateRoster(self):
		self.logger.debug("Update roster")

		old = self.buddies.keys()
		self.buddies.load()
		new = self.buddies.keys()
		contacts = new

		if self.synced == False:
			self.sendSync(contacts, delta = False, interactive = True)
			self.synced = True

		add = set(new) - set(old)
		remove = set(old) - set(new)

		self.logger.debug("Roster remove: %s", str(list(remove)))
		self.logger.debug("Roster add: %s", str(list(add)))

		for number in remove:
			self.backend.handleBuddyChanged(self.user, number, "", [],
											protocol_pb2.STATUS_NONE)
			self.backend.handleBuddyRemoved(self.user, number)
			self.unsubscribePresence(number)

		for number in add:
			buddy = self.buddies[number]
			self.subscribePresence(number)
			self.backend.handleBuddyChanged(self.user, number, buddy.nick,
				buddy.groups, protocol_pb2.STATUS_NONE,
				iconHash = buddy.image_hash if buddy.image_hash is not None else "")

			#self.requestLastSeen(number, self._lastSeen)

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
				self.joinRoom(self._shortenGroupId(room), self.user.split("@")[0])

			self._addParticipantsToRoom(room, group.getParticipants())

			if room in self.groupOfflineQueue:
				while self.groupOfflineQueue[room]:
					msg = self.groupOfflineQueue[room].pop(0)
					self.backend.handleMessage(self.user, room, msg[1],
											   msg[0], "", msg[2])
					self.logger.debug("Send queued group message to: %s %s %s",
									  msg[0],msg[1], msg[2])
		self.updateRoomList()

	def joinRoom(self, room, nick):
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

			self.backend.handleSubject(self.user, self._shortenGroupId(room),
									   group.subject,
									   ownerNick)
			self.backend.handleRoomNicknameChanged(
				self.user, self._shortenGroupId(room), group.subject
			)
			self._refreshParticipants(room)
		else:
			self.logger.warn("Room doesn't exist: %s", room)

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

			buddyFull = buddy 
			if buddy == group.owner:
				flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
			else:
				flags = protocol_pb2.PARTICIPANT_FLAG_NONE
			if buddy == self.legacyName:
				nick = group.nick
				flags = flags | protocol_pb2.PARTICIPANT_FLAG_ME
				buddyFull = self.user
			self.backend.handleParticipantChanged(
				self.user, buddyFull, self._shortenGroupId(room), flags,
				protocol_pb2.STATUS_ONLINE, buddy, nick)

	def _addParticipantsToRoom(self, room, participants):
		group = self.groups[room]
		group.participants = participants

		for jid, _type in participants.iteritems():
			buddy = jid.split("@")[0]
			buddyFull = buddy
			self.logger.info("Added %s to room %s", buddy, room)
			try:
				nick = self.buddies[buddy].nick
			except KeyError:
				nick = buddy
				buddyFull = buddy
			if _type == 'admin':
				flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
			else:
				flags = protocol_pb2.PARTICIPANT_FLAG_NONE
				if buddy == self.legacyName:
					nick = group.nick
					flags = protocol_pb2.PARTICIPANT_FLAG_ME
					buddyFull = self.user

			self.backend.handleParticipantChanged(
				self.user, buddyFull, self._shortenGroupId(room), flags,
				protocol_pb2.STATUS_ONLINE, buddy, nick
			)


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
			self.bot.call("welcome")
			self.initialized = True
		self.sendPresence(True)
		self.updateRoster()

		self.logger.debug('Requesting groups list')
		self.requestGroupsList(self._updateGroups)

	# Called by superclass
	def onAuthFailed(self, reason):
		self.logger.info("Auth failed: %s (%s)", self.user, reason)
		self.backend.handleDisconnected(self.user, 0, reason)
		self.password = None
		self.shouldBeConnected = False

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
			self.backend.handleBuddyChanged(self.user, buddy.number.number,
					buddy.nick, buddy.groups, protocol_pb2.STATUS_ONLINE)
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
						self.user, partname, buddy,
						protocol_pb2.PARTICIPANT_FLAG_NONE,
						protocol_pb2.STATUS_NONE, "", part.nick
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
		message = image.url + ' ' + image.caption
		self.sendMessageToXMPP(buddy, message, image.timestamp)
		self.sendReceipt(image._id,	 image._from, None, image.participant)

	# Called by superclass
	def onAudio(self, audio):
		self.logger.debug('Received audio message %s', str(audio))
		buddy = audio._from.split('@')[0]
		message = audio.url
		self.sendMessageToXMPP(buddy, message, audio.timestamp)
		self.sendReceipt(audio._id,	 audio._from, None, audio.participant)

	# Called by superclass
	def onVideo(self, video):
		self.logger.debug('Received video message %s', str(video))
		buddy = video._from.split('@')[0]
		message = video.url
		self.sendMessageToXMPP(buddy, message, video.timestamp)
		self.sendReceipt(video._id,	 video._from, None, video.participant)

	def onLocation(self, location):
		buddy = location._from.split('@')[0]
		latitude = location.getLatitude()
		longitude = location.getLongitude()
		url = location.getLocationUrl()

		self.logger.debug("Location received from %s: %s, %s",
						  buddy, latitude, longitude)

		self.sendMessageToXMPP(buddy, url, location.timestamp)
		self.sendMessageToXMPP(buddy, 'geo:' + latitude + ',' + longitude,
							   location.timestamp)


	# Called by superclass
	def onVCard(self, _id, _from, name, card_data, to, notify, timestamp, participant):
		self.logger.debug('received VCard' +
			' '.join(map(str, [
				_id, _from, name, card_data, to, notify, timestamp, participant
			]))
		)
		buddy = _from.split("@")[0]
		self.sendMessageToXMPP(buddy, "Received VCard (not implemented yet)")
#		self.sendMessageToXMPP(buddy, card_data)
		self.transferFile(buddy, str(name), card_data)
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

	def onPresenceReceived(self, _type, name, jid, lastseen):
		self.logger.info("Presence received: %s %s %s %s", _type, name, jid, lastseen)
		buddy = jid.split("@")[0]
#		seems to be causing an error
#		self.logger.info("Lastseen: %s %s", buddy, utils.ago(lastseen))

		if buddy in self.presenceRequested:
			timestamp = time.localtime(time.time() - lastseen)
			timestring = time.strftime("%a, %d %b %Y %H:%M:%S", timestamp)
			self.sendMessageToXMPP(buddy, "%s (%s)" % (timestring, utils.ago(lastseen)))
			self.presenceRequested.remove(buddy)

		if lastseen < 60:
			self.onPresenceAvailable(buddy)
		else:
			self.onPresenceUnavailable(buddy)

	def onPresenceAvailable(self, buddy):
		try:
			buddy = self.buddies[buddy]
			self.logger.info("Is available: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number,
				buddy.nick, buddy.groups, protocol_pb2.STATUS_ONLINE)
		except KeyError:
			self.logger.error("Buddy not found: %s", buddy)

	def onPresenceUnavailable(self, buddy):
		try:
			buddy = self.buddies[buddy]
			self.logger.info("Is unavailable: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number,
				buddy.nick, buddy.groups, protocol_pb2.STATUS_XA)
		except KeyError:
			self.logger.error("Buddy not found: %s", buddy)

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

	def sendMessageToWA(self, sender, message):
		self.logger.info("Message sent from %s to %s: %s",
						 self.legacyName, sender, message)

		message = message.encode("utf-8")

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
				self.sendTextMessage(nick + '@s.whatsapp.net', message)
			else:
				room = sender
				try:
					group = self.groups[self._lengthenGroupId(room)]
					self.logger.info("Group Message from %s to %s Groups: %s",
									 group.nick , group , self.groups)
					self.backend.handleMessage(
						self.user, room, message.decode('utf-8'), group.nick
					)
				except KeyError:
					self.logger.error('Group not found: %s', room)
				self.sendTextMessage(self._lengthenGroupId(room) + '@g.us', message)

		else: # private msg
			buddy = sender
#			if message == "\\lastseen":
#				self.call("presence_request", buddy = (buddy + "@s.whatsapp.net",))
#			else:
			self.sendTextMessage(sender + '@s.whatsapp.net', message)

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
		self._refreshParticipants(room)
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

			if self.initialized == False:
				self.sendOfflineMessages()
				self.bot.call("welcome")
				self.initialized = True

	def sendOfflineMessages(self):
		# Flush Queues
		while self.offlineQueue:
			msg = self.offlineQueue.pop(0)
			self.backend.handleMessage(self.user, msg[0], msg[1], "", "", msg[2])

	# also for adding a new buddy
	def updateBuddy(self, buddy, nick, groups, image_hash = None):
		if buddy != "bot":
			self.buddies.update(buddy, nick, groups, image_hash)
			self.updateRoster()

	def removeBuddy(self, buddy):
		if buddy != "bot":
			self.logger.info("Buddy removed: %s", buddy)
			self.buddies.remove(buddy)
			self.updateRoster()


	def requestVCard(self, buddy, ID):
		def onSuccess(response, request):
			self.logger.debug('Sending VCard (%s) with image id %s',
					ID, response.pictureId)
			image_hash = utils.sha1hash(response.pictureData)
			self.logger.debug('Image hash is %s', image_hash)
			self.backend.handleVCard(self.user, ID, buddy, "", "", response.pictureData)
			obuddy = self.buddies[buddy]
			self.updateBuddy(buddy, obuddy.nick, obuddy.groups, image_hash)

		self.logger.debug('Requesting profile picture of %s', buddy)
		self.requestProfilePicture(buddy, onSuccess = onSuccess)

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
