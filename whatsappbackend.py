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
import hashlib
import logging

class WhatsAppBackend(SpectrumBackend):
	def __init__(self, io, db):
		SpectrumBackend.__init__(self)
		self.logger = logging.getLogger(self.__class__.__name__)
                #self.logger = logging.getLogger('Transwhat Backend')
                #self.logger.setLevel(logging.DEBUG)
                #ch = logging.StreamHandler()
                #ch.setLevel(logging.DEBUG)
                #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                #ch.setFormatter(formatter)
                #self.logger.addHandler(ch)
		self.io = io
		self.db = db
		self.sessions = { }

		self.logger.debug("Backend started")

	# RequestsHandlers
	def handleLoginRequest(self, user, legacyName, password, extra):
		self.logger.info("handleLoginRequest(user=%s, legacyName=%s)", user, legacyName)
		if user not in self.sessions:
			self.sessions[user] = Session(self, user, legacyName, extra, self.db)
                        self.logger.info("handleLoginRequest Create (user=%s, legacyName=%s)", user, legacyName)


		self.sessions[user].login(password)

	def handleLogoutRequest(self, user, legacyName):
		self.logger.info("handleLogoutRequest(user=%s, legacyName=%s)", user, legacyName)
		if user in self.sessions:
			self.sessions[user].logout()
			del self.sessions[user]

	def handleMessageSendRequest(self, user, buddy, message, xhtml = "", ID = 0):
		self.logger.info("handleMessageSendRequest(user=%s, buddy=%s, message=%s, id=%s)", user, buddy, message, ID)
		if user not in self.sessions:
                        return;
		self.sessions[user].sendMessageToWA(buddy, message, ID)
                #self.handleMessageAck(user, buddy, ID)

	def handleJoinRoomRequest(self, user, room, nickname, pasword):
		self.logger.debug("handleJoinRoomRequest(user=%s, room=%s, nickname=%s)", user, room, nickname)
		if user not in self.sessions:
                        return;
		self.sessions[user].joinRoom(room, nickname, False)

	def handleStatusChangeRequest(self, user, status, statusMessage):
		self.logger.debug("handleStatusChangeRequest(user=%s, status=%d, statusMessage=%s)", user, status, statusMessage)
		if user not in self.sessions:
                        return;
		self.sessions[user].changeStatusMessage(statusMessage)
		self.sessions[user].changeStatus(status)

	def handleBuddyUpdatedRequest(self, user, buddy, nick, groups):
		self.logger.debug("handleBuddyUpdatedRequest(user=%s, buddy=%s, nick=%s, groups=%s)", user, buddy, nick, str(groups))
		if user not in self.sessions:
                        return;
		self.sessions[user].updateBuddy(buddy, nick, groups)

	def handleBuddyRemovedRequest(self, user, buddy, groups):
		self.logger.debug("handleBuddyRemovedRequest(user=%s, buddy=%s, groups=%s)", user, buddy, str(groups))
		if user not in self.sessions:
                        return;
		self.sessions[user].removeBuddy(buddy)

	def handleTypingRequest(self, user, buddy):
		self.logger.debug("handleTypingRequest(user=%s, buddy=%s)", user, buddy)
		if user not in self.sessions:
                        return;
		self.sessions[user].sendTypingStarted(buddy)

	def handleTypedRequest(self, user, buddy):
		self.logger.debug("handleTypedRequest(user=%s, buddy=%s)", user, buddy)
		if user not in self.sessions:
                        return;
		self.sessions[user].sendTypingStopped(buddy)

	def handleStoppedTypingRequest(self, user, buddy):
		self.logger.debug("handleStoppedTypingRequest(user=%s, buddy=%s)", user, buddy)
		if user not in self.sessions:
                        return;

		self.sessions[user].sendTypingStopped(buddy)

	# TODO
	def handleBuddyBlockToggled(self, user, buddy, blocked):
		pass

	def handleLeaveRoomRequest(self, user, room):
		pass

	def handleVCardRequest(self, user, buddy, ID):
                self.logger.info("VCard requested for %s !!",buddy)
		if user not in self.sessions:
			return;
                #self.sessions[user].call("contact_getProfilePicture", (buddy + "@s.whatsapp.net",))
                #sql = 'UPDATE numbers SET picture=%s WHERE number=%s'
                #args = (blob_value,buddy, )
                #self.logger.info("Insert Picture SQL: %s, args: %s", sql, args)
                cursor=self.db.cursor()
                cursor.execute('SELECT picture FROM numbers WHERE number=%s', (buddy,))
                #self.db.commit()
                if not (cursor.rowcount == 0): 
                    (pic,) = cursor.fetchone()
                    #pic=file('/tmp/tmpJoMbLq','rb')
                    self.handleVCard(user,ID,buddy,"","",pic)
		    m = hashlib.sha1()
                    m.update(pic)
		    try:
		    	#self.sessions[user].call("presence_request", (buddy + "@s.whatsapp.net",))
		    	buddy = self.sessions[user].buddies[buddy]
		    	buddy.iconHash = m.hexdigest()
		    except KeyError:
			self.logger.error("VCard: User(%s) Buddy not found:  %s !!",user,buddy)
                
		

	def handleVCardUpdatedRequest(self, user, photo, nickname):
                self.logger.info("VCard update requested")
		pass

	def handleAttentionRequest(self, user, buddy, message):
                self.logger.info("Attetion request for %s !!",buddy)
		pass

	def handleFTStartRequest(self, user, buddy, fileName, size, ftID):
		self.logger.info("FT Start request for %s !!",buddy)
                pass

	def handleFTFinishRequest(self, user, buddy, fileName, size, ftID):
                self.logger.info("FT Finish request for %s !!",buddy)
		pass

	def handleFTPauseRequest(self, ftID):
                self.logger.info("FT Pause request")
		pass

	def handleFTContinueRequest(self, ftID):
                self.logger.info("FT Continue request")
		pass

	def handleRawXmlRequest(self, xml):
                #self.logger.info("Raw XML request")

		self.logger.info("Raw XML: %s", xml)
		pass

	def handleMessageAckRequest(self, user, legacyName, ID = 0):
		self.logger.info("Meassage ACK request for %s !!",leagcyName)

	def sendData(self, data):
		self.io.sendData(data)

