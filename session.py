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

from yowsup.stacks import YowStack
from yowsup.layers import YowLayerEvent, YowParallelLayer
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup.layers.auth import (YowCryptLayer, YowAuthenticationProtocolLayer,
								AuthError)
from yowsup.layers.protocol_iq import YowIqProtocolLayer
from yowsup.layers.protocol_groups import YowGroupsProtocolLayer
from yowsup.layers.coder import YowCoderLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.protocol_media import YowMediaProtocolLayer
from yowsup.layers.stanzaregulator import YowStanzaRegulator
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.layers.logger import YowLoggerLayer
from yowsup.common import YowConstants
from yowsup.layers.protocol_receipts.protocolentities	 import *
from yowsup import env
from yowsup.layers.protocol_presence import *
from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_acks.protocolentities	 import *
from yowsup.layers import YowLayer
from yowsup.layers.auth						   import YowCryptLayer, YowAuthenticationProtocolLayer
from yowsup.layers.coder					   import YowCoderLayer
from yowsup.layers.logger					   import YowLoggerLayer
from yowsup.layers.network					   import YowNetworkLayer
from yowsup.layers.protocol_messages		   import YowMessagesProtocolLayer
from yowsup.layers.stanzaregulator			   import YowStanzaRegulator
from yowsup.layers.protocol_media			   import YowMediaProtocolLayer
from yowsup.layers.protocol_acks			   import YowAckProtocolLayer
from yowsup.layers.protocol_receipts		   import YowReceiptProtocolLayer
from yowsup.layers.protocol_groups			   import YowGroupsProtocolLayer
from yowsup.layers.protocol_presence		   import YowPresenceProtocolLayer
from yowsup.layers.protocol_ib				   import YowIbProtocolLayer
from yowsup.layers.protocol_notifications	   import YowNotificationsProtocolLayer
from yowsup.layers.protocol_iq				   import YowIqProtocolLayer
from yowsup.layers.protocol_contacts		   import YowContactsIqProtocolLayer
from yowsup.layers.protocol_chatstate		   import YowChatstateProtocolLayer
from yowsup.layers.protocol_privacy			   import YowPrivacyProtocolLayer
from yowsup.layers.protocol_profiles		   import YowProfilesProtocolLayer
from yowsup.layers.protocol_calls import YowCallsProtocolLayer
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
		self.buddies = BuddyList(self.legacyName, self.db)
		self.bot = Bot(self)

		self.status = protocol_pb2.STATUS_NONE
		self.statusMessage = ''

		self.groups = {}
		self.presenceRequested = []
		self.offlineQueue = []
		self.groupOfflineQueue = { }

		self.timer = None
		self.password = None
		self.initialized = False
		self.loggedin = False

		self.bot = Bot(self)

	def __del__(self): # handleLogoutRequest
		self.logout()

	def call(self, method, **kwargs):
		self.logger.debug("%s(%s)", method,
				", ".join(str(k) + ': ' + str(v) for k, v in kwargs.items()))
		##self.stack.broadcastEvent(YowLayerEvent(method, **kwargs))

	def logout(self):
		self.loggedin = False
		super(Session, self).logout()

	def login(self, password):
		self.loggedin = True
		self.password = password
		super(Session, self).login(self.legacyName, self.password)

	def updateRoomList(self):
		rooms = []
		for room, group in self.groups.iteritems():
			rooms.append([room, group.subject])

		self.backend.handleRoomList(rooms)

	def updateRoster(self):
		self.logger.debug("Update roster")

		old = self.buddies.keys()
		self.buddies.load()
		new = self.buddies.keys()

		add = set(new) - set(old)
		remove = set(old) - set(new)

		self.logger.debug("Roster remove: %s", str(list(remove)))
		self.logger.debug("Roster add: %s", str(list(add)))

		for number in remove:
			self.backend.handleBuddyChanged(self.user, number, "", [], protocol_pb2.STATUS_NONE)
			self.backend.handleBuddyRemoved(self.user, number)
#			entity = UnsubscribePresenceProtocolEntity(number + "@s.whatsapp.net")
#			self.toLower(entity)

		for number in add:
			buddy = self.buddies[number]
#			entity = SubscribePresenceProtocolEntity(number + "@s.whatsapp.net")
#			self.toLower(entity)

	# Called by superclass
	def onAuthSuccess(self, status, kind, creation,
			expiration, props, nonce, t):
		self.logger.info("Auth success: %s", self.user)

		self.backend.handleConnected(self.user)
		self.backend.handleBuddyChanged(self.user, "bot", self.bot.name, ["Admin"], protocol_pb2.STATUS_ONLINE)
		self.initialized = True

		self.updateRoster()

	# Called by superclass
	def onAuthFailed(self, reason):
		self.logger.info("Auth failed: %s (%s)", self.user, reason)
		self.backend.handleDisconnected(self.user, 0, reason)
		self.password = None
	
	# Called by superclass
	def onDisconnect(self):
		self.logger.debug('Disconnected')
		self.backend.handleDisconnected(self.user, 0, 'Disconnected for unknown reasons')
		self.loggedin = False

	# Called by superclass
	def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
		self.logger.debug("received receipt, sending ack: " +
				' '.join(map(str, [_id, _from, timestamp,
					type, participant, offline, items]))
		)

	# Called by superclass
	def onAck(self, _id,_class, _from, timestamp):
		self.logger.debug('received ack ' + 
				' '.join(map(str, [_id, _class, _from,timestamp,]))
		)

	# Called by superclass
	def onMessage(self, messageEntity):
		self.logger.debug(str(messageEntity))
		buddy = messageEntity.getFrom().split('@')[0]
		messageContent = utils.softToUni(messageEntity.getBody())
		timestamp = messageEntity.getTimestamp()

		self.sendReceipt(messageEntity.getId(), messageEntity.getFrom(), None,
				messageEntity.getParticipant())

		if messageEntity.isBroadcast():
			self.logger.info("Broadcast received from %s to %s: %s (at ts=%s)",\
					buddy, self.legacyName, messageContent, timestamp)
			messageContent = "[Broadcast] " + messageContent
		else:
			self.logger.info("Message received from %s to %s: %s (at ts=%s)",
					buddy, self.legacyName, messageContent, timestamp)
			self.sendMessageToXMPP(buddy, messageContent, timestamp)

		# if receiptRequested: self.call("message_ack", (jid, messageId))

	# spectrum RequestMethods
	def sendTypingStarted(self, buddy):
		if buddy != "bot":
			self.logger.info("Started typing: %s to %s", self.legacyName, buddy)
			self.call("typing_send", buddy = (buddy + "@s.whatsapp.net",))

	def sendTypingStopped(self, buddy):
		if buddy != "bot":
			self.logger.info("Stopped typing: %s to %s", self.legacyName, buddy)
			self.call("typing_paused", buddy = (buddy + "@s.whatsapp.net",))

	def sendMessageToWA(self, sender, message):
		self.logger.info("Message sent from %s to %s: %s", self.legacyName, sender, message)
		message = message.encode("utf-8")

#		if sender == "bot":
#			self.bot.parse(message)
#		elif "-" in sender: # group msg
#			if "/" in sender:
#				room, buddy = sender.split("/")
#				self.sendTextMessage(buddy + '@s.whatsapp.net', message)
#			else:
#				room = sender
#				group = self.groups[room]
#
#				self.backend.handleMessage(self.user, room, message, group.nick)
#				self.sendTextMessage(room + '@g.us', message)
#
#		else: # private msg
#			buddy = sender
#			if message == "\\lastseen":
#				self.presenceRequested.append(buddy)
#				self.call("presence_request", buddy = (buddy + "@s.whatsapp.net",))
#			else:
		self.sendTextMessage(sender + '@s.whatsapp.net', message)

	def sendMessageToXMPP(self, buddy, messageContent, timestamp = ""):
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
		if timestamp:
			timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

		if self.initialized == False:
			self.logger.debug("Group message queued from %s to %s: %s", buddy, room, messageContent)

			if room not in self.groupOfflineQueue:
				self.groupOfflineQueue[room] = [ ]

			self.groupOfflineQueue[room].append((buddy, messageContent, timestamp))
		else:
			self.logger.debug("Group message sent from %s to %s: %s", buddy, room, messageContent) 
			self.backend.handleMessage(self.user, room, messageContent, buddy, "", timestamp)

	def changeStatus(self, status):
		if status != self.status:
			self.logger.info("Status changed: %s", status)
			self.status = status

			if status == protocol_pb2.STATUS_ONLINE or status == protocol_pb2.STATUS_FFC:
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
	def updateBuddy(self, buddy, nick, groups):
		if buddy != "bot":
			self.buddies.update(buddy, nick, groups)
			self.updateRoster()

	def removeBuddy(self, buddy):
		if buddy != "bot":
			self.logger.info("Buddy removed: %s", buddy)
			self.buddies.remove(buddy)
			self.updateRoster()

	def joinRoom(self, room, nick):
		if room in self.groups:
			group = self.groups[room]

			self.logger.info("Joining room: %s room=%s, nick=%s", self.legacyName, room, nick)

			group.nick = nick

			self.call("group_getParticipants", (room + "@g.us",))
			self.backend.handleSubject(self.user, room, group.subject, group.subjectOwner)
		else:
			self.logger.warn("Room doesn't exist: %s", room)

	def onMediaReceived(self, messageId, jid, preview, url, size,  receiptRequested, isBroadcast):
		buddy = jid.split("@")[0]

		self.logger.info("Media received from %s: %s", buddy, url)
		self.sendMessageToXMPP(buddy, utils.shorten(url))
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onLocationReceived(self, messageId, jid, name, preview, latitude, longitude, receiptRequested, isBroadcast):
		buddy = jid.split("@")[0]
		self.logger.info("Location received from %s: %s, %s", buddy, latitude, longitude)

		url = "http://maps.google.de?%s" % urllib.urlencode({ "q": "%s %s" % (latitude, longitude) })
		self.sendMessageToXMPP(buddy, utils.shorten(url))
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onVcardReceived(self, messageId, jid, name, data, receiptRequested, isBroadcast): # TODO
		buddy = jid.split("@")[0]
		self.logger.info("VCard received from %s", buddy)
		self.sendMessageToXMPP(buddy, "Received VCard (not implemented yet)")
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onContactTyping(self, jid):
		buddy = jid.split("@")[0]
		self.logger.info("Started typing: %s", buddy)
		self.backend.handleBuddyTyping(self.user, buddy)

		if self.timer != None:
			self.timer.cancel()

	def onContactPaused(self, jid):
		buddy = jid.split("@")[0]
		self.logger.info("Paused typing: %s", buddy)
		self.backend.handleBuddyTyped(self.user, jid.split("@")[0])
		self.timer = Timer(3, self.backend.handleBuddyStoppedTyping, (self.user, buddy)).start()

	def onGroupGotInfo(self, gjid, owner, subject, subjectOwner, subjectTimestamp, creationTimestamp):
		room = gjid.split("@")[0]
		owner = owner.split("@")[0]
		subjectOwner = subjectOwner.split("@")[0]

		if room in self.groups:
			room = self.groups[room]
			room.owner = owner
			room.subjectOwner = subjectOwner
			room.subject = subject
		else:
			self.groups[room] = Group(room, owner, subject, subjectOwner)

		self.updateRoomList()

	def onGroupGotParticipants(self, gjid, jids):
		room = gjid.split("@")[0]
		group = self.groups[room]

		for jid in jids:
			buddy = jid.split("@")[0]
			self.logger.info("Added %s to room %s", buddy, room)

			if buddy == group.owner:
				flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
			else:
				flags = protocol_pb2.PARTICIPANT_FLAG_NONE

			self.backend.handleParticipantChanged(self.user, buddy, room, flags, protocol_pb2.STATUS_ONLINE) # TODO check status

			if room in self.groupOfflineQueue:
				while self.groupOfflineQueue[room]:
					msg = self.groupOfflineQueue[room].pop(0)
					self.backend.handleMessage(self.user, room, msg[1], msg[0], "", msg[2])
					self.logger.debug("Send queued group message to: %s %s %s", msg[0],msg[1], msg[2])

	def onGroupMessageReceived(self, messageId, gjid, jid, messageContent, timestamp, receiptRequested, pushName):
		buddy = jid.split("@")[0]
		room = gjid.split("@")[0]

		self.logger.info("Group message received in  %s from %s: %s", room, buddy, messageContent)

		self.sendGroupMessageToXMPP(room, buddy, utils.softToUni(messageContent), timestamp)
		if receiptRequested: self.call("message_ack", (gjid, messageId))

	def onGroupSubjectReceived(self, messageId, gjid, jid, subject, timestamp, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		self.backend.handleSubject(self.user, room, subject, buddy)
		if receiptRequested: self.call("subject_ack", (gjid, messageId))

	# Yowsup Notifications
	def onGroupParticipantAdded(self, gjid, jid, author, timestamp, messageId, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		loggin.info("Added % to room %s", buddy, room)

		self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_ONLINE)
		if receiptRequested: self.call("notification_ack", (gjid, messageId))

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

class SpectrumLayer(YowInterfaceLayer):
	EVENT_START = "transwhat.event.SpectrumLayer.start"

	def onEvent(self, layerEvent):
		# We cannot use __init__, since it can take no arguments
		retval = False
		if layerEvent.getName() == SpectrumLayer.EVENT_START:
			self.logger = logging.getLogger(self.__class__.__name__)
			self.backend = layerEvent.getArg("backend")
			self.user = layerEvent.getArg("user")
			self.legacyName = layerEvent.getArg("legacyName")
			self.db = layerEvent.getArg("db")
			self.session = layerEvent.getArg("session")

			self.session.buddies = BuddyList(self.legacyName, self.db)
			self.bot = Bot(self)
			retval = True
		elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
			reason = layerEvent.getArg("reason")
			self.logger.info("Disconnected: %s (%s)", self.user, reason)
			self.backend.handleDisconnected(self.user, 0, reason)
#		elif layerEvent.getName() == 'presence_sendAvailable':
#			entity = AvailablePresenceProtocolEntity()
#			self.toLower(entity)
#			retval = True
#		elif layerEvent.getName() == 'presence_sendUnavailable':
#			entity = UnavailablePresenceProtocolEntity()
#			self.toLower(entity)
#			retval = True
#		elif layerEvent.getName() == 'profile_setStatus':
#			# entity = PresenceProtocolEntity(name = layerEvent.getArg('message'))
#			entity = PresenceProtocolEntity(name = 'This status is non-empty')
#			self.toLower(entity)
#			retval = True
#		elif layerEvent.getName() == 'message_send':
#			to = layerEvent.getArg('to')
#			message = layerEvent.getArg('message')
#			messageEntity = TextMessageProtocolEntity(message, to = to)
#			self.toLower(messageEntity)
#			retval = True
		elif layerEvent.getName() == 'typing_send':
			buddy = layerEvent.getArg('buddy')
			state = OutgoingChatstateProtocolEntity(
					ChatstateProtocolEntity.STATE_TYPING, buddy
					)
			self.toLower(state)
			retval = True
		elif layerEvent.getName() == 'typing_paused':
			buddy = layerEvent.getArg('buddy')
			state = OutgoingChatstateProtocolEntity(
					ChatstateProtocolEntity.STATE_PAUSED, buddy
					)
			self.toLower(state)
			retval = True
		elif layerEvent.getName() == 'presence_request':
			buddy = layerEvent.getArg('buddy')
			sub = SubscribePresenceProtocolEntity(buddy)
			self.toLower(sub)

		self.logger.debug("EVENT %s", layerEvent.getName())
		return retval

	@ProtocolEntityCallback("presence")
	def onPrecenceUpdated(self, presence):
		jid = presence.getFrom()
		lastseen = presence.getLast()
		buddy = jid.split("@")[0]
#		seems to be causing an error
#		self.logger.info("Lastseen: %s %s", buddy, utils.ago(lastseen))

		if buddy in self.session.presenceRequested:
			timestamp = time.localtime(time.time() - lastseen)
			timestring = time.strftime("%a, %d %b %Y %H:%M:%S", timestamp)
			self.session.sendMessageToXMPP(buddy, "%s (%s)" % (timestring, utils.ago(lastseen)))
			self.session.presenceRequested.remove(buddy)

		if lastseen < 60:
			self.onPrecenceAvailable(jid)
		else:
			self.onPrecenceUnavailable(jid)

	def onPrecenceAvailable(self, jid):
		buddy = jid.split("@")[0]

		try:
			buddy = self.session.buddies[buddy]
			self.logger.info("Is available: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number, buddy.nick, buddy.groups, protocol_pb2.STATUS_ONLINE)
		except KeyError:
			self.logger.error("Buddy not found: %s", buddy)

	def onPrecenceUnavailable(self, jid):
		buddy = jid.split("@")[0]

		try:
			buddy = self.session.buddies[buddy]
			self.logger.info("Is unavailable: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number, buddy.nick, buddy.groups, protocol_pb2.STATUS_XA)
		except KeyError:
			self.logger.error("Buddy not found: %s", buddy)

