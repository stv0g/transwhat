import logging
import spectrum2

from .session import Session
from .registersession import RegisterSession


class WhatsAppBackend(spectrum2.Backend):
    def __init__(self, io, spectrum_jid, specConf):
        super().__init__(self)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.io = io
        self.specConf = specConf
        self.sessions = {}
        self.spectrum_jid = spectrum_jid
        # Used to prevent duplicate messages
        self.lastMsgId = {}

        self.logger.debug("Backend started")

    # RequestsHandlers
    def handle_login_request(self, user, legacyName, password, extra):
        self.logger.debug(
            "handleLoginRequest(user=%s, legacyName=%s)" % (user, legacyName)
        )
        # Key word means we should register a new password
        if password == "register":
            if user not in self.sessions:
                self.sessions[user] = RegisterSession(self, user, legacyName, extra)
        else:
            if user not in self.sessions:
                self.sessions[user] = Session(self, user, legacyName, extra)

        self.sessions[user].login(password)

    def handle_logout_request(self, user, legacyName):
        self.logger.debug(
            "handleLogoutRequest(user=%s, legacyName=%s)" % (user, legacyName)
        )
        if user in self.sessions:
            self.sessions[user].logout()
            del self.sessions[user]

    def handle_message_send_request(self, user, buddy, message, xhtml="", ID=""):
        self.logger.debug(
            "handleMessageSendRequest(user=%s, buddy=%s, message=%s, xhtml=%s, ID=%s)"
            % (user, buddy, message, xhtml, ID)
        )
        # For some reason spectrum occasionally sends to identical messages to
        # a buddy, one to the bare jid and one to the /bot resource. This
        # causes duplicate messages. Thus we should not send consecutive
        # messages with the same id
        if ID == "":
            self.sessions[user].sendMessageToWA(buddy, message, ID, xhtml)
        elif user not in self.lastMsgId or self.lastMsgId[user] != ID:
            self.sessions[user].sendMessageToWA(buddy, message, ID, xhtml)
            self.lastMsgId[user] = ID

    def handle_join_room_request(self, user, room, nickname, pasword):
        self.logger.debug(
            "handleJoinRoomRequest(user=%s, room=%s, nickname=%s)"
            % (user, room, nickname)
        )
        self.sessions[user].joinRoom(room, nickname)

    def handle_leave_room_request(self, user, room):
        self.logger.debug("handleLeaveRoomRequest(user=%s, room=%s)" % (user, room))
        self.sessions[user].leaveRoom(room)

    def handle_status_change_request(self, user, status, statusMessage):
        self.logger.debug(
            "handleStatusChangeRequest(user=%s, status=%d, statusMessage=%s)"
            % (user, status, statusMessage)
        )
        self.sessions[user].changeStatusMessage(statusMessage)
        self.sessions[user].changeStatus(status)

    def handleBuddies(self, buddies):
        """Called when user logs in. Used to initialize roster."""
        self.logger.debug("handleBuddies(buddies=%s)" % buddies)
        buddies = [b for b in buddies.buddy]
        if len(buddies) > 0:
            user = buddies[0].userName
            self.sessions[user].loadBuddies(buddies)

    def handleBuddyUpdatedRequest(self, user, buddy, nick, groups):
        self.logger.debug(
            "handleBuddyUpdatedRequest(user=%s, buddy=%s, nick=%s, groups=%s)"
            % (user, buddy, nick, groups)
        )
        self.sessions[user].updateBuddy(buddy, nick, groups)

    def handleBuddyRemovedRequest(self, user, buddy, groups):
        self.logger.debug(
            "handleBuddyRemovedRequest(user=%s, buddy=%s, groups=%s)"
            % (user, buddy, groups)
        )
        self.sessions[user].removeBuddy(buddy)

    def handleTypingRequest(self, user, buddy):
        self.logger.debug("handleTypingRequest(user=%s, buddy=%s)" % (user, buddy))
        self.sessions[user].sendTypingStarted(buddy)

    def handleTypedRequest(self, user, buddy):
        self.logger.debug("handleTypedRequest(user=%s, buddy=%s)" % (user, buddy))
        self.sessions[user].sendTypingStopped(buddy)

    def handleStoppedTypingRequest(self, user, buddy):
        self.logger.debug(
            "handleStoppedTypingRequest(user=%s, buddy=%s)" % (user, buddy)
        )
        self.sessions[user].sendTypingStopped(buddy)

    def handleVCardRequest(self, user, buddy, ID):
        self.logger.debug(
            "handleVCardRequest(user=%s, buddy=%s, ID=%s)" % (user, buddy, ID)
        )
        self.sessions[user].requestVCard(buddy, ID)

    def handleVCardUpdatedRequest(self, user, photo, nickname):
        self.logger.debug(
            "handleVCardUpdatedRequest(user=%s, nickname=%s)" % (user, nickname)
        )
        self.sessions[user].setProfilePicture(photo)

    def handleBuddyBlockToggled(self, user, buddy, blocked):
        self.logger.debug(
            "handleBuddyBlockedToggled(user=%s, buddy=%s, blocked=%s)"
            % (user, buddy, blocked)
        )

    def relogin(self, user, legacyName, password, extra):
        """
        Used to re-initialize the session object. Used when finished with
        registration session and the user needs to login properly
        """
        self.logger.debug("relogin(user=%s, legacyName=%s)" % (user, legacyName))
        # Change password in spectrum database
        self.handle_query("register %s %s %s" % (user, legacyName, password))
        # Key word means we should register a new password
        if password == "register":  # This shouldn't happen, but just in case
            self.sessions[user] = RegisterSession(self, user, legacyName, extra)
        else:
            self.sessions[user] = Session(self, user, legacyName, extra)
        self.sessions[user].login(password)

    # TODO
    def handleAttentionRequest(self, user, buddy, message):
        pass

    def handleFTStartRequest(self, user, buddy, fileName, size, ftID):
        self.logger.debug(
            "File send request %s, for user %s, from %s, size: %s"
            % (fileName, user, buddy, size)
        )

    def handleFTFinishRequest(self, user, buddy, fileName, size, ftID):
        pass

    def handleFTPauseRequest(self, ftID):
        pass

    def handleFTContinueRequest(self, ftID):
        pass

    def handleRawXmlRequest(self, xml):
        pass

    def handleMessageAckRequest(self, user, legacyName, ID=0):
        self.logger.info("Meassage ACK request for %s !!" % legacyName)

    def sendData(self, data):
        self.io.send_data(data)
