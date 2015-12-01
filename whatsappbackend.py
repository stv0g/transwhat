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

from Spectrum2.backend import SpectrumBackend
from Spectrum2 import protocol_pb2

from session import Session

import logging

class WhatsAppBackend(SpectrumBackend):
	def __init__(self, io, db, spectrum_jid):
		SpectrumBackend.__init__(self)
		self.logger = logging.getLogger(self.__class__.__name__)
		self.io = io
		self.db = db
		self.sessions = { }
		self.spectrum_jid = spectrum_jid
		# Used to prevent duplicate messages
		self.lastMessage = {}

		self.logger.debug("Backend started")

	# RequestsHandlers
	def handleLoginRequest(self, user, legacyName, password, extra):
		self.logger.debug("handleLoginRequest(user=%s, legacyName=%s)", user, legacyName)
		if user not in self.sessions:
			self.sessions[user] = Session(self, user, legacyName, extra, self.db)

		if user not in self.lastMessage:
			self.lastMessage[user] = {}

		self.sessions[user].login(password)

	def handleLogoutRequest(self, user, legacyName):
		self.logger.debug("handleLogoutRequest(user=%s, legacyName=%s)", user, legacyName)
		if user in self.sessions:
			self.sessions[user].logout()
			del self.sessions[user]

	def handleMessageSendRequest(self, user, buddy, message, xhtml = "", ID =  0):
		self.logger.debug("handleMessageSendRequest(user=%s, buddy=%s, message=%s, xhtml = %s)", user, buddy, message, xhtml)
		# For some reason spectrum occasionally sends to identical messages to
		# a buddy, one to the bare jid and one to /bot. This causes duplicate
		# messages. Since it is unlikely a user wants to send the same message
		# twice, we should just ignore the second message
		#
		# TODO Proper fix, this work around drops all duplicate messages even 
		# intentional ones.
                # IDEA there is an ID field in ConvMessage. If it is extracted it will work
		usersMessage = self.lastMessage[user]
		if buddy not in usersMessage or usersMessage[buddy] != message:
			self.sessions[user].sendMessageToWA(buddy, message, ID)
			usersMessage[buddy] = message

	def handleJoinRoomRequest(self, user, room, nickname, pasword):
		self.logger.debug("handleJoinRoomRequest(user=%s, room=%s, nickname=%s)", user, room, nickname)
		self.sessions[user].joinRoom(room, nickname)

	def handleLeaveRoomRequest(self, user, room):
		self.logger.debug("handleLeaveRoomRequest(user=%s, room=%s)", user, room)
		self.sessions[user].leaveRoom(room)

	def handleStatusChangeRequest(self, user, status, statusMessage):
		self.logger.debug("handleStatusChangeRequest(user=%s, status=%d, statusMessage=%s)", user, status, statusMessage)
		self.sessions[user].changeStatusMessage(statusMessage)
		self.sessions[user].changeStatus(status)

	def handleBuddies(self, buddies):
		"""Called when user logs in. Used to initialize roster."""
		self.logger.debug("handleBuddies(buddies=%s)", buddies)
		buddies = [b for b in buddies.buddy]
		user = buddies[0].userName
		self.sessions[user].loadBuddies(buddies)

	def handleBuddyUpdatedRequest(self, user, buddy, nick, groups):
		self.logger.debug("handleBuddyUpdatedRequest(user=%s, buddy=%s, nick=%s, groups=%s)", user, buddy, nick, str(groups))
		self.sessions[user].updateBuddy(buddy, nick, groups)

	def handleBuddyRemovedRequest(self, user, buddy, groups):
		self.logger.debug("handleBuddyRemovedRequest(user=%s, buddy=%s, groups=%s)", user, buddy, str(groups))
		self.sessions[user].removeBuddy(buddy)

	def handleTypingRequest(self, user, buddy):
		self.logger.debug("handleTypingRequest(user=%s, buddy=%s)", user, buddy)
		self.sessions[user].sendTypingStarted(buddy)

	def handleTypedRequest(self, user, buddy):
		self.logger.debug("handleTypedRequest(user=%s, buddy=%s)", user, buddy)
		self.sessions[user].sendTypingStopped(buddy)

	def handleStoppedTypingRequest(self, user, buddy):
		self.logger.debug("handleStoppedTypingRequest(user=%s, buddy=%s)", user, buddy)
		self.sessions[user].sendTypingStopped(buddy)

	def handleVCardRequest(self, user, buddy, ID):
		self.logger.debug("handleVCardRequest(user=%s, buddy=%s, ID=%s)", user, buddy, ID)
		self.sessions[user].requestVCard(buddy, ID)


	# TODO
	def handleBuddyBlockToggled(self, user, buddy, blocked):
		pass

	def handleVCardUpdatedRequest(self, user, photo, nickname):
		pass

	def handleAttentionRequest(self, user, buddy, message):
		pass

	def handleFTStartRequest(self, user, buddy, fileName, size, ftID):
		self.logger.debug('File send request %s, for user %s, from %s, size: %s',
				fileName, user, buddy, size)

	def handleFTFinishRequest(self, user, buddy, fileName, size, ftID):
		pass

	def handleFTPauseRequest(self, ftID):
		pass

	def handleFTContinueRequest(self, ftID):
		pass

	def handleRawXmlRequest(self, xml):
		pass

 	def handleMessageAckRequest(self, user, legacyName, ID = 0):
                self.logger.info("Meassage ACK request for %s !!",legacyName)

	def sendData(self, data):
		self.io.sendData(data)

