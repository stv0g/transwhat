import utils
import logging
import urllib
import time

from Yowsup.connectionmanager import YowsupConnectionManager
from Spectrum2 import protocol_pb2

from buddy import BuddyList
from threading import Timer
from group import Group
from bot import Bot
from constants import *

class Session:

	def __init__(self, backend, user, legacyName, password, extra, db):
		logging.info("new session: %s %s", legacyName, extra)

		password = base64.b64decode(bytes(password.encode('utf-8')))

		e4u.load()

		self.db = db
		self.backend = backend
		self.user = user
		self.status = protocol_pb2.STATUS_NONE
		self.statusMessage = ''
		self.legacyName = legacyName
		self.groups = { }
		self.timer = None

		self.roster = Roster(legacyName, db)
		self.frontend = YowsupConnectionManager()

		# Events
		self.listen("auth_success", self.onAuthSuccess)
		self.listen("auth_fail", self.onAuthFailed)

		self.listen("contact_typing", self.onContactTyping)
		self.listen("contact_paused", self.onContactPaused)

		self.listen("presence_updated", self.onPrecenceUpdated)
		self.listen("presence_available", self.onPrecenceAvailable)
		self.listen("presence_unavailable", self.onPrecenceUnavailable)

		self.listen("message_received", self.onMessageReceived)
		self.listen("image_received", self.onMediaReceived)
		self.listen("video_received", self.onMediaReceived)
		self.listen("audio_received", self.onMediaReceived)
		self.listen("location_received", self.onLocationReceived)
		self.listen("vcard_received", self.onVcardReceived)

		self.listen("group_messageReceived", self.onGroupMessageReceived)
		self.listen("group_gotInfo", self.onGroupGotInfo)
		self.listen("group_gotParticipants", self.onGroupGotParticipants)
		self.listen("group_subjectReceived", self.onGroupSubjectReceived)
		self.listen("notification_groupParticipantAdded", self.onGroupParticipantAdded)
		self.listen("notification_groupParticipantRemoved", self.onGroupParticipantRemoved)
		self.call("auth_login", (legacyName, password))

	def __del__(self):
		self.call("disconnect", ("logout",))

	def _softToUni(self, message):
		message = unicode(message, "utf-8")
		return e4u.translate(message, reverse=False, **e4u.SOFTBANK_TRANSLATE_PROFILE)

	def call(self, method, args = ()):
		self.frontend.methodInterface.call(method, args)

	def listen(self, event, callback):
		self.frontend.signalInterface.registerListener(event, callback)

	# RequestMethods
	def sendTypingStarted(self, buddy):
		logging.info("started typing: %s to %s", self.legacyName, buddy)
		self.call("typing_send", (buddy + "@s.whatsapp.net",))

	def sendTypingStopped(self, buddy):
		logging.info("stopped typing: %s to %s", self.legacyName, buddy)
		self.call("typing_paused", (buddy + "@s.whatsapp.net",))

	def sendMessage(self, sender, message):
		logging.info("message send to %s: %s", sender, message)
		message = message.encode("utf-8")

		if ("-" in sender): # group msg
			if ("/" in sender):
				room, buddy = sender.split("/")
				self.call("message_send", (buddy + "@s.whatsapp.net", message))
			else:
				room = sender
				self.backend.handleMessage(self.user, room, message, "me") # TODO
				self.call("message_send", (room + "@g.us", message))
		else: # private msg
			buddy = sender
			self.call("message_send", (buddy + "@s.whatsapp.net", message))

	def changeStatus(self, status):
		if (status == self.status): return

		logging.info("status changed: %s", status)
		self.status = status
		if (status == protocol_pb2.STATUS_ONLINE):
			self.call("presence_sendAvailable")
		elif (status == protocol_pb2.STATUS_FFC):
			self.call("presence_sendAvailableForChat")
		else:
			self.call("presence_sendUnavailable")

	def changeStatusMessage(self, statusMessage):
		if (statusMessage == self.statusMessage): return

		logging.info("status message changed: %s", statusMessage)
		self.statusMessage = statusMessage
		self.call("profile_setStatus", (statusMessage.encode("utf-8"),))

	def updateBuddy(self, buddy, nick, groups):
		if self.roster.buddies.has_key(buddy):
			buddy = self.roster.buddies[buddy]
			buddy.update(nick)
			logging.info("buddy renamed: %s", buddy)
			self.call("presence_request", (buddy.number.number + "@s.whatsapp.net",))
		else:
			self.roster.add(buddy, nick)
			self.call("presence_request", (buddy + "@s.whatsapp.net",))
			self.backend.handleBuddyChanged(self.user, buddy, nick, [], protocol_pb2.STATUS_NONE)

	def removeBuddy(self, buddy):
		self.roster.remove(buddy)

	def joinRoom(self, room):
		self.call("group_getParticipants", (room + "@g.us",))

	# EventHandlers
	def onAuthSuccess(self, user):
		logging.info("auth success: %s", user)
		self.backend.handleConnected(self.user)
		self.call("ready")

		self.call("group_getGroups", ("participating",))

		self.roster.load()
		for number, buddy in self.roster.buddies.iteritems():
			logging.info("request presence: %s", buddy)
			self.call("presence_request", (buddy.number.number + "@s.whatsapp.net",))
			self.backend.handleBuddyChanged(self.user, buddy.number.number, buddy.nick, [], protocol_pb2.STATUS_NONE)

	def onAuthFailed(self, user, reason):
		logging.info("auth failed: %s (%s)", user, reason)
		self.backend.handleDisconnected(self.user, 0, reason)

	def onMessageReceived(self, messageId, jid, messageContent, timestamp, receiptRequested, pushName, isBroadCast):
		buddy = jid.split("@")[0]
		logging.info("message received from %s: %s", buddy, messageContent)
		self.backend.handleMessage(self.user, buddy, self._softToUni(messageContent), timestamp=timestamp)
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onMediaReceived(self, messageId, jid, preview, url, size,  receiptRequested, isBroadcast):
		buddy = jid.split("@")[0]
		logging.info("message received from %s: %s", buddy, url)
		self.backend.handleMessage(self.user, buddy, url)
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onLocationReceived(self, messageId, jid, name, preview, latitude, longitude, receiptRequested, isBroadcast):
		buddy = jid.split("@")[0]
		logging.info("location received from %s: %s, %s", buddy, latitude, longitude)
		self.backend.handleMessage(self.user, buddy, "http://maps.google.de?%s" % urllib.urlencode({ "q": "%s %s" % (latitude, longitude) }))
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onVcardReceived(self, messageId, jid, name, data, receiptRequested, isBroadcast): # TODO
		buddy = jid.split("@")[0]
		logging.info("vcard received from %s", buddy)
		self.backend.handleMessage(self.user, buddy, "Received VCard (not implemented yet)")
		if receiptRequested: self.call("message_ack", (jid, messageId))

	def onContactTyping(self, jid):
		buddy = jid.split("@")[0]
		logging.info("started typing: %s", buddy)
		self.backend.handleBuddyTyping(self.user, buddy)
		if (self.timer != None): self.timer.cancel()

	def onContactPaused(self, jid):
		buddy = jid.split("@")[0]
		logging.info("paused typing: %s", buddy)
		self.backend.handleBuddyTyped(self.user, jid.split("@")[0])
		self.timer = Timer(3, self.backend.handleBuddyStoppedTyping, (self.user, buddy)).start()

	def onPrecenceUpdated(self, jid, lastseen):
		buddy = jid.split("@")[0]
		logging.info("lastseen: %s %d secs ago", buddy, lastseen)
		if (lastseen < 60): self.onPrecenceAvailable(jid)
		else: self.onPrecenceUnavailable(jid)

	def onPrecenceAvailable(self, jid):
		buddy = jid.split("@")[0]
		if (self.roster.buddies.has_key(buddy)):
			buddy = self.roster.buddies[buddy]
			logging.info("is available: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number, buddy.nick, [], protocol_pb2.STATUS_ONLINE)

	def onPrecenceUnavailable(self, jid):
		buddy = jid.split("@")[0]
		if (self.roster.buddies.has_key(buddy)):
			buddy = self.roster.buddies[buddy]
			logging.info("is unavailable: %s", buddy)
			self.backend.handleBuddyChanged(self.user, buddy.number.number, buddy.nick, [], protocol_pb2.STATUS_XA)

	def onGroupGotInfo(self, gjid, owner, subject, subjectOwner, subjectTimestamp, creationTimestamp):
		room = gjid.split("@")[0]

		if self.groups.has_key(room):
			room = self.groups[room]
			room.owner = owner
			room.subject = subject
		else:
			self.groups = Group(room, subject, owner)

		self.backend.handleRoomList([[room, subject]])

	def onGroupGotParticipants(self, gjid, jids):
		room = gjid.split("@")[0]

		for jid in jids:
			buddy = jid.split("@")[0]
			logging.info("added %s to room %s", buddy, room)
			self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_ONLINE)

		self.backend.handleParticipantChanged(self.user, self.legacyName, room, protocol_pb2.PARTICIPANT_FLAG_ME, protocol_pb2.STATUS_ONLINE)
		# TODO check status and moderator

	def onGroupMessageReceived(self, messageId, gjid, jid, messageContent, timestamp, receiptRequested, pushName):
		buddy = jid.split("@")[0]
		room = gjid.split("@")[0]

		logging.info("group message received in  %s from %s: %s", room, buddy, messageContent)
		self.backend.handleMessage(self.user, room, self._softToUni(messageContent), buddy, timestamp=timestamp)
		if receiptRequested: self.call("message_ack", (gjid, messageId))

	def onGroupSubjectReceived(self, messageId, gjid, jid, subject, timestamp, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		self.backend.handleSubject(self.user, room, subject, buddy)
		if receiptRequested: self.call("subject_ack", (gjid, messageId))

	def onGroupParticipantAdded(self, gjid, jid, author, timestamp, messageId, receiptRequested):
		room = gjid.split("@")[0]
		buddy = jid.split("@")[0]

		self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_ONLINE)
#		if receiptRequested: self.call("message_ack", (gjid, messageId))

	def onGroupParticipantRemoved(gjid, jid, author, timestamp, messageId, receiptRequested):
		self.backend.handleParticipantChanged(self.user, buddy, room, protocol_pb2.PARTICIPANT_FLAG_NONE, protocol_pb2.STATUS_NONE) # TODO
#		if receiptRequested: self.call("message_ack", (gjid, messageId))
