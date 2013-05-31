from Spectrum2.backend import SpectrumBackend
from Spectrum2 import protocol_pb2

from session import Session

import logging

class WhatsAppBackend(SpectrumBackend):
	def __init__(self, io, db):
		SpectrumBackend.__init__(self)
		self.io = io
		self.db = db
		self.sessions = { }

#		self.handleBackendConfig("features", "muc", "true")
#		self.handleBackendConfig("features", "rawxml", "true")

		logging.info("initialized backend")

	# RequestsHandlers
	def handleLoginRequest(self, user, legacyName, password, extra):
		self.sessions[user] = Session(self, user, legacyName, password, extra, self.db)

	def handleLogoutRequest(self, user, legacyName):
		del self.sessions[user]

	def handleMessageSendRequest(self, user, buddy, message, xhtml = ""):
		self.sessions[user].sendMessage(buddy, message)

	def handleVCardRequest(self, user, buddy, ID):
		# TODO
		pass

	def handleVCardUpdatedRequest(self, user, photo, nickname):
		# TODO
		pass

	def handleJoinRoomRequest(self, user, room, nickname, pasword):
		self.sessions[user].joinRoom(room)

	def handleLeaveRoomRequest(self, user, room):
		pass

	def handleStatusChangeRequest(self, user, status, statusMessage):
		if (len(statusMessage)):
			self.sessions[user].changeStatusMessage(statusMessage)
		self.sessions[user].changeStatus(status)

	def handleBuddyUpdatedRequest(self, user, buddy, nick, groups):
		self.sessions[user].updateBuddy(buddy, nick, groups)

	def handleBuddyRemovedRequest(self, user, buddy, groups):
		self.sessions[user].removeBuddy(buddy)

	def handleBuddyBlockToggled(self, user, buddy, blocked):
		pass

	def handleTypingRequest(self, user, buddy):
		self.sessions[user].sendTypingStarted(buddy)

	def handleTypedRequest(self, user, buddy):
		self.sessions[user].sendTypingStopped(buddy)

	def handleStoppedTypingRequest(self, user, buddy):
		self.sessions[user].sendTypingStopped(buddy)

	def handleAttentionRequest(self, user, buddy, message):
		# TODO
		pass

	def handleFTStartRequest(self, user, buddy, fileName, size, ftID):
		pass

	def handleFTFinishRequest(self, user, buddy, fileName, size, ftID):
		pass

	def handleFTPauseRequest(self, ftID):
		pass

	def handleFTContinueRequest(self, ftID):
		pass

	def handleRawXmlRequest(self, xml):
		pass

	def sendData(self, data):
		self.io.sendData(data)


