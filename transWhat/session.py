import logging
import urllib
import time
import os

from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_media.mediadownloader import MediaDownloader

import spectrum2

from . import deferred
from .buddy import BuddyList
from .group import Group
from .bot import Bot
from .yowsupwrapper import YowsupApp


def ago(secs):
    periods = ["second", "minute", "hour", "day", "week", "month", "year", "decade"]
    lengths = [60, 60, 24, 7, 4.35, 12, 10]

    j = 0
    diff = secs

    while diff >= lengths[j]:
        diff /= lengths[j]
        diff = round(diff)
        j += 1

    period = periods[j]
    if diff > 1:
        period += "s"

    return "%d %s ago" % (diff, period)


class MsgIDs:
    def __init__(self, xmppId, waId):
        self.xmppId = xmppId
        self.waId = waId
        self.cnt = 0


class Session(YowsupApp):
    broadcast_prefix = "\U0001F4E2 "

    def __init__(self, backend, user, legacyName, extra):
        super().__init__()

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Created: %s" % legacyName)

        self.backend = backend
        self.user = user
        self.legacyName = legacyName

        self.status = spectrum2.protocol_pb2.STATUS_NONE
        self.statusMessage = ""

        self.groups = {}
        self.gotGroupList = False
        # Functions to exectute when logged in via yowsup
        self.loginQueue = []
        self.joinRoomQueue = []
        self.presenceRequested = []
        self.offlineQueue = []
        self.msgIDs = {}
        self.groupOfflineQueue = {}
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
        self.imgPath = ""
        self.imgBuddy = None
        self.imgType = ""

    def __del__(self):  # handleLogoutRequest
        self.logout()

    def logout(self):
        # Do not logout when there is no way that we are logged in
        if not self.loggedIn:
            self.logger.info("%s already logged out, ignoring" % self.user)
            return

        # Log out otherwise
        self.logger.info("%s logged out" % self.user)
        super().logout()
        self.loggedIn = False

    def login(self, password):
        self.logger.info("%s attempting login" % self.user)
        self.password = password
        self.shouldBeConncted = True
        super().login(self.legacyName, self.password)

    def _shortenGroupId(self, gid):
        # FIXME: might have problems if number begins with 0
        return gid

    #        return '-'.join(hex(int(s))[2:] for s in gid.split('-'))

    def _lengthenGroupId(self, gid):
        return gid
        # FIXME: might have problems if number begins with 0

    #        return '-'.join(str(int(s, 16)) for s in gid.split('-'))

    def updateRoomList(self):
        rooms = []
        text = []
        for room, group in self.groups.items():
            rooms.append([self._shortenGroupId(room), group.subject])
            text.append(
                self._shortenGroupId(room)
                + "@"
                + self.backend.spectrum_jid
                + " :"
                + group.subject
            )

        self.logger.debug("Got rooms: %s" % rooms)
        self.backend.handleRoomList(rooms)
        message = (
            "Note, you are a participant of the following groups:\n"
            + "\n".join(text)
            + "\nIf you do not join them you will lose messages"
        )
        # self.bot.send(message)

    def _updateGroups(self, response, _):
        self.logger.debug("Received groups list %s" % response)
        groups = response.getGroups()
        for group in groups:
            room = group.getId()
            # ensure self.groups[room] exists
            if room not in self.groups:
                owner = group.getOwner().split("@")[0]
                subjectOwner = group.getSubjectOwner().split("@")[0]
                subject = group.getSubject()
                self.groups[room] = Group(
                    room, owner, subject, subjectOwner, self.backend, self.user
                )
            # add/update room participants
            self.groups[room].addParticipants(
                group.getParticipants().keys(), self.buddies, self.legacyName
            )
        self.gotGroupList = True
        # join rooms
        while self.joinRoomQueue:
            self.joinRoom(*self.joinRoomQueue.pop(0))
        # deliver queued offline messages
        for room in self.groupOfflineQueue:
            while self.groupOfflineQueue[room]:
                msg = self.groupOfflineQueue[room].pop(0)
                self.backend.handleMessage(self.user, room, msg[1], msg[0], "", msg[2])
                self.logger.debug(
                    "Send queued group message to: %s %s %s" % (msg[0], msg[1], msg[2])
                )
        # pass update to backend
        self.updateRoomList()

    def joinRoom(self, room, nick):
        if not self.gotGroupList:
            self.joinRoomQueue.append((room, nick))
            return
        room = self._lengthenGroupId(room)
        if room in self.groups:
            self.logger.info(
                "Joining room: %s room=%s, nick=%s" % (self.legacyName, room, nick)
            )

            group = self.groups[room]
            group.joined = True
            group.nick = nick
            group.participants[self.legacyName] = nick
            try:
                ownerNick = group.participants[group.subjectOwner]
            except KeyError:
                ownerNick = group.subjectOwner

            group.sendParticipantsToSpectrum(self.legacyName)
            self.backend.handleSubject(
                self.user, self._shortenGroupId(room), group.subject, ownerNick
            )
            self.logger.debug(
                "Room subject: room=%s, subject=%s" % (room, group.subject)
            )
            self.backend.handleRoomNicknameChanged(
                self.user, self._shortenGroupId(room), group.subject
            )
        else:
            self.logger.warn("Room doesn't exist: %s" % room)

    def leaveRoom(self, room):
        if room in self.groups:
            self.logger.info("Leaving room: %s room=%s" % (self.legacyName, room))
            group = self.groups[room]
            group.joined = False
        else:
            self.logger.warn("Room doesn't exist: %s. Unable to leave." % room)

    def _lastSeen(self, number, seconds):
        self.logger.debug("Last seen %s at %s seconds" % (number, seconds))
        if seconds < 60:
            self.onPresenceAvailable(number)
        else:
            self.onPresenceUnavailable(number)

    def sendReadReceipts(self, buddy):
        for _id, _from, participant, t in self.recvMsgIDs:
            if _from.split("@")[0] == buddy:
                self.sendReceipt(_id, _from, "read", participant)
                self.recvMsgIDs.remove((_id, _from, participant, t))
                self.logger.debug("Send read receipt to %s (ID: %s)", _from, _id)

    # Called by superclass
    def onAuthSuccess(self, status, kind, creation, expiration, props, nonce, t):
        self.logger.info("Auth success: %s" % self.user)

        self.backend.handle_connected(self.user)
        self.backend.handle_buddy_changed(
            self.user,
            "bot",
            self.bot.name,
            ["Admin"],
            spectrum2.protocol_pb2.STATUS_ONLINE,
        )
        # Initialisation?
        self.requestPrivacyList()
        self.requestClientConfig()
        self.requestServerProperties()
        # ?

        self.logger.debug("Requesting groups list")

        # TODO: updateGroups is broken
        # TODO:
        # TODO: it also calls methods which do not
        # TODO: exist in pyspectrum2
        # self.requestGroupsList(self._updateGroups)

        # self.requestBroadcastList()

        # This should handle, sync, statuses, and presence
        self.sendPresence(True)
        for func in self.loginQueue:
            func()

        if self.initialized == False:
            self.sendOfflineMessages()
            # self.bot.call("welcome")
            self.initialized = True

        self.loggedIn = True

    # Called by superclass
    def onAuthFailed(self, reason):
        self.logger.info("Auth failed: %s (%s)" % (self.user, reason))
        self.backend.handle_disconnected(self.user, 0, reason)
        self.password = None
        self.loggedIn = False

    # Called by superclass
    def onDisconnect(self):
        self.logger.debug("Disconnected")
        self.backend.handle_disconnected(
            self.user, 0, "Disconnected for unknown reasons"
        )

    # Called by superclass
    def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
        self.logger.debug(
            "received receipt, sending ack: %s"
            % [_id, _from, timestamp, type, participant, offline, items]
        )
        try:
            number = _from.split("@")[0]
            self.backend.handleMessageAck(self.user, number, self.msgIDs[_id].xmppId)
            self.msgIDs[_id].cnt = self.msgIDs[_id].cnt + 1
            if self.msgIDs[_id].cnt == 2:
                del self.msgIDs[_id]
        except KeyError:
            self.logger.error("Message %s not found. Unable to send ack" % _id)

    # Called by superclass
    def onAck(self, _id, _class, _from, timestamp):
        self.logger.debug("received ack: %s" % [_id, _class, _from, timestamp])

    # Called by superclass
    def onTextMessage(
        self, _id, _from, to, notify, timestamp, participant, offline, retry, body
    ):
        buddy = _from.split("@")[0]
        messageContent = body
        self.sendReceipt(_id, _from, None, participant)
        self.recvMsgIDs.append((_id, _from, participant, timestamp))
        self.logger.info(
            "Message received from %s to %s: %s (at ts=%s)"
            % (buddy, self.legacyName, messageContent, timestamp)
        )

        if participant is not None:  # Group message or broadcast
            partname = participant.split("@")[0]
            if _from.split("@")[1] == "broadcast":  # Broadcast message
                message = self.broadcast_prefix + messageContent
                self.sendMessageToXMPP(partname, message, timestamp)
            else:  # Group message
                if notify is None:
                    notify = ""
                self.sendGroupMessageToXMPP(
                    buddy, partname, messageContent, timestamp, notify
                )
        else:
            self.sendMessageToXMPP(buddy, messageContent, timestamp)

    # Called by superclass
    def onImage(self, image):
        if image.caption is None:
            image.caption = ""

        self.onMedia(image, "image")

    # Called by superclass
    def onAudio(self, audio):
        self.onMedia(audio, "audio")

    # Called by superclass
    def onVideo(self, video):
        self.onMedia(video, "video")

    def onMedia(self, media, type):
        self.logger.debug("Received %s message: %s" % (type, media))
        buddy = media.getFrom(full=False)
        participant = media.participant
        url = media.url
        caption = ""

        # TODO: media.isEncrypted does not exist anymore(?)
        # if media.isEncrypted():
        #    self.logger.debug('Received encrypted media message')
        #    if self.backend.specConf is not None and self.backend.specConf.__getitem__("service.web_directory") is not None and self.backend.specConf.__getitem__("service.web_url") is not None :
        #        ipath = "/" + str(media.timestamp)  + media.getExtension()

        #        with open(self.backend.specConf.__getitem__("service.web_directory") + ipath,"wb") as f:
        #            f.write(media.getMediaContent())
        #        url = self.backend.specConf.__getitem__("service.web_url") + ipath
        #    else:
        #        self.logger.warn('Received encrypted media: web storage not set in config!')
        #        url = media.url

        # else:

        if type == "image":
            caption = media.caption

        if participant is not None:  # Group message
            partname = participant.split("@")[0]
            if media._from.split("@")[1] == "broadcast":  # Broadcast message
                self.sendMessageToXMPP(
                    partname, self.broadcast_prefix, media.getTimestamp()
                )
                self.sendMessageToXMPP(partname, url, media.getTimestamp())
                self.sendMessageToXMPP(partname, caption, media.getTimestamp())
            else:  # Group message
                self.sendGroupMessageToXMPP(buddy, partname, url, media.getTimestamp())
                self.sendGroupMessageToXMPP(
                    buddy, partname, caption, media.getTimestamp()
                )
        else:
            self.sendMessageToXMPP(buddy, url, media.getTimestamp())
            self.sendMessageToXMPP(buddy, caption, media.getTimestamp())

        self.sendReceipt(media.getId(), media.getFrom(), None, media.participant)
        self.recvMsgIDs.append(
            (media.getId(), media.getFrom(), media.participant, media.getTimestamp())
        )

    def onLocation(self, location):
        buddy = location._from.split("@")[0]
        latitude = location.getLatitude()
        longitude = location.getLongitude()
        url = location.getLocationURL()
        participant = location.participant
        latlong = "geo:" + latitude + "," + longitude

        self.logger.debug(
            "Location received from %s: %s, %s", (buddy, latitude, longitude)
        )

        if participant is not None:  # Group message
            partname = participant.split("@")[0]
            if location._from.split("@")[1] == "broadcast":  # Broadcast message
                self.sendMessageToXMPP(
                    partname, self.broadcast_prefix, location.timestamp
                )
                if url is not None:
                    self.sendMessageToXMPP(partname, url, location.timestamp)
                self.sendMessageToXMPP(partname, latlong, location.timestamp)
            else:  # Group message
                if url is not None:
                    self.sendGroupMessageToXMPP(
                        buddy, partname, url, location.timestamp
                    )
                self.sendGroupMessageToXMPP(
                    buddy, partname, latlong, location.timestamp
                )
        else:
            if url is not None:
                self.sendMessageToXMPP(buddy, url, location.timestamp)
            self.sendMessageToXMPP(buddy, latlong, location.timestamp)
        self.sendReceipt(location._id, location._from, None, location.participant)
        self.recvMsgIDs.append(
            (location._id, location._from, location.participant, location.timestamp)
        )

    # Called by superclass
    def onVCard(self, _id, _from, name, card_data, to, notify, timestamp, participant):
        self.logger.debug(
            "received VCard: %s"
            % [_id, _from, name, card_data, to, notify, timestamp, participant]
        )
        message = "Received VCard (not implemented yet)"
        buddy = _from.split("@")[0]
        if participant is not None:  # Group message
            partname = participant.split("@")[0]
            if _from.split("@")[1] == "broadcast":  # Broadcast message
                message = self.broadcast_prefix + message
                self.sendMessageToXMPP(partname, message, timestamp)
            else:  # Group message
                self.sendGroupMessageToXMPP(buddy, partname, message, timestamp)
        else:
            self.sendMessageToXMPP(buddy, message, timestamp)
        #        self.sendMessageToXMPP(buddy, card_data)
        # self.transferFile(buddy, str(name), card_data)
        self.sendReceipt(_id, _from, None, participant)
        self.recvMsgIDs.append((_id, _from, participant, timestamp))

    def transferFile(self, buddy, name, data):
        # Not working
        self.logger.debug("transfering file: %s" % name)
        self.backend.handleFTStart(self.user, buddy, name, len(data))
        self.backend.handleFTData(0, data)
        self.backend.handleFTFinish(self.user, buddy, name, len(data), 0)

    # Called by superclass
    def onContactTyping(self, buddy):
        self.logger.info("Started typing: %s" % buddy)
        if buddy != "bot":
            self.sendPresence(True)
            self.backend.handleBuddyTyping(self.user, buddy)

            if self.timer != None:
                self.timer.cancel()

    # Called by superclass
    def onContactPaused(self, buddy):
        self.logger.info("Paused typing: %s" % buddy)
        if buddy != "bot":
            self.backend.handleBuddyTyped(self.user, buddy)
            self.timer = threading.Timer(
                3, self.backend.handleBuddyStoppedTyping, (self.user, buddy)
            ).start()

    # Called by superclass
    def onAddedToGroup(self, group):
        self.logger.debug("Added to group: %s" % group)
        room = group.getGroupId()
        owner = group.getCreatorJid(full=False)
        subjectOwner = group.getSubjectOwnerJid(full=False)
        subject = group.getSubject()

        self.groups[room] = Group(
            room, owner, subject, subjectOwner, self.backend, self.user
        )
        self.groups[room].addParticipants(
            group.getParticipants(), self.buddies, self.legacyName
        )
        self.bot.send(
            "You have been added to group: %s@%s (%s)"
            % (self._shortenGroupId(room), subject, self.backend.spectrum_jid)
        )

    # Called by superclass
    def onParticipantsAddedToGroup(self, group):
        self.logger.debug("Participants added to group: %s" % group)
        room = group.getGroupId().split("@")[0]
        self.groups[room].addParticipants(
            group.getParticipants(), self.buddies, self.legacyName
        )
        self.groups[room].sendParticipantsToSpectrum(self.legacyName)

    # Called by superclass
    def onSubjectChanged(self, room, subject, subjectOwner, timestamp):
        self.logger.debug(
            "onSubjectChange(rrom=%s, subject=%s, subjectOwner=%s, timestamp=%s)"
            % (room, subject, subjectOwner, timestamp)
        )
        try:
            group = self.groups[room]
        except KeyError:
            self.logger.error("Subject of non-existant group (%s) changed" % group)
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
        self.logger.debug(
            "Participants removed from group: %s, %s" % (room, participants)
        )
        self.groups[room].removeParticipants(participants)

    # Called by superclass
    def onContactStatusChanged(self, number, status):
        self.logger.debug("%s changed their status to %s" % (number, status))
        try:
            buddy = self.buddies[number]
            buddy.statusMsg = status
            self.buddies.updateSpectrum(buddy)
        except KeyError:
            self.logger.debug("%s not in buddy list" % number)

    # Called by superclass
    def onContactPictureChanged(self, number):
        self.logger.debug("%s changed their profile picture" % number)
        self.buddies.requestVCard(number)

    # Called by superclass
    def onContactAdded(self, number, nick):
        self.logger.debug("Adding new contact %s (%s)" % (nick, number))
        self.updateBuddy(number, nick, [])

    # Called by superclass
    def onContactRemoved(self, number):
        self.logger.debug("Removing contact %s" % number)
        self.removeBuddy(number)

    def onContactUpdated(self, oldnumber, newnumber):
        self.logger.debug(
            "Contact has changed number from %s to %s" % (oldnumber, newnumber)
        )
        if newnumber in self.buddies:
            self.logger.warn("Contact %s exists, just updating" % newnumber)
            self.buddies.refresh(newnumber)
        try:
            buddy = self.buddies[oldnumber]
        except KeyError:
            self.logger.warn(
                "Old contact (%s) not found. Adding new contact (%s)"
                % (oldnumber, newnumber)
            )
            nick = ""
        else:
            self.removeBuddy(buddy.number)
            nick = buddy.nick
        self.updateBuddy(newnumber, nick, [])

    def onPresenceReceived(self, _type, name, jid, lastseen):
        self.logger.info(
            "Presence received: %s %s %s %s" % (_type, name, jid, lastseen)
        )
        buddy = jid.split("@")[0]
        try:
            buddy = self.buddies[buddy]
        except KeyError:
            # Sometimes whatsapp send our own presence
            if buddy != self.legacyName:
                self.logger.error("Buddy not found: %s" % buddy)
            return

        if (lastseen == buddy.lastseen) and (_type == buddy.presence):
            return

        if (lastseen != "deny") and (lastseen != None) and (lastseen != "none"):
            buddy.lastseen = int(lastseen)
        if _type == None:
            buddy.lastseen = time.time()

        buddy.presence = _type

        if _type == "unavailable":
            self.onPresenceUnavailable(buddy)
        else:
            self.onPresenceAvailable(buddy)

    def onPresenceAvailable(self, buddy):
        self.logger.info("Is available: %s" % buddy)
        self.buddies.updateSpectrum(buddy)

    def onPresenceUnavailable(self, buddy):
        self.logger.info("Is unavailable: %s" % buddy)
        self.buddies.updateSpectrum(buddy)

    # spectrum RequestMethods
    def sendTypingStarted(self, buddy):
        if buddy != "bot":
            self.logger.info("Started typing: %s to %s" % (self.legacyName, buddy))
            self.sendTyping(buddy, True)
            self.sendReadReceipts(buddy)
        # If he is typing he is present
        # I really don't know where else to put this.
        # Ideally, this should be sent if the user is looking at his client
        self.sendPresence(True)

    def sendTypingStopped(self, buddy):
        if buddy != "bot":
            self.logger.info("Stopped typing: %s to %s" % (self.legacyName, buddy))
            self.sendTyping(buddy, False)
            self.sendReadReceipts(buddy)

    def sendImage(self, message, ID, to):
        if ".jpg" in message.lower():
            imgType = "jpg"
        if ".webp" in message.lower():
            imgType = "webp"

        success = deferred.Deferred()
        error = deferred.Deferred()
        self.downloadMedia(message, success.run, error.run)

        # Success
        path = success.arg(0)
        call(self.logger.info, "Success: Image downloaded to %s" % path)
        pathWithExt = path.then(lambda p: p + "." + imgType)
        call(os.rename, path, pathWithExt)
        pathJpg = path.then(lambda p: p + ".jpg")
        if imgType != "jpg":
            im = call(Image.open, pathWithExt)
            call(im.save, pathJpg)
            call(os.remove, pathWithExt)
        call(self.logger.info, "Sending image to %s" % to)
        waId = deferred.Deferred()
        call(super().sendImage, to, pathJpg, onSuccess=waId.run)
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
        self.logger.info(
            "Message sent from %s to %s: %s (xhtml=%s)"
            % (self.legacyName, sender, message, xhtml)
        )

        self.sendReadReceipts(sender)

        if sender == "bot":
            self.bot.parse(message)
        elif "-" in sender:  # group msg
            if "/" in sender:  # directed at single user
                room, nick = sender.split("/")
                group = self.groups[room]
                number = None
                for othernumber, othernick in group.participants.iteritems():
                    if othernick == nick:
                        number = othernumber
                        break
                if number is not None:
                    self.logger.debug(
                        "Private message sent from %s to %s" % (self.legacyName, number)
                    )
                    waId = self.sendTextMessage(number + "@s.whatsapp.net", message)
                    self.msgIDs[waId] = MsgIDs(ID, waId)
                else:
                    self.logger.error(
                        "Attempted to send private message to non-existent user"
                    )
                    self.logger.debug("%s to %s in %s" % (self.legacyName, nick, room))
            else:
                room = sender
                if message[0] == "\\" and message[:1] != "\\\\":
                    self.logger.debug("Executing command %s in %s" % (message, room))
                    self.executeCommand(message, room)
                else:
                    try:
                        group = self.groups[self._lengthenGroupId(room)]
                        self.logger.debug(
                            "Group Message from %s to %s Groups: %s"
                            % (group.nick, group, self.groups)
                        )
                        self.backend.handleMessage(
                            self.user, room, message, group.nick, xhtml=xhtml
                        )
                    except KeyError:
                        self.logger.error("Group not found: %s" % room)

                if (".jpg" in message.lower()) or (".webp" in message.lower()):
                    self.sendImage(message, ID, room + "@g.us")
                elif "geo:" in message.lower():
                    self._sendLocation(room + "@g.us", message, ID)
                else:
                    self.sendTextMessage(room + "@g.us", message)
        else:  # private msg
            buddy = sender
            if message.split(" ").pop(0) == "\\lastseen":
                self.presenceRequested.append(buddy)
                self._requestLastSeen(buddy)
            elif message.split(" ").pop(0) == "\\gpp":
                self.sendMessageToXMPP(buddy, "Fetching Profile Picture")
                self.requestVCard(buddy)
            elif (".jpg" in message.lower()) or (".webp" in message.lower()):
                self.sendImage(message, ID, buddy + "@s.whatsapp.net")
            elif "geo:" in message.lower():
                self._sendLocation(buddy + "@s.whatsapp.net", message, ID)
            else:
                waId = self.sendTextMessage(sender + "@s.whatsapp.net", message)
                self.msgIDs[waId] = MsgIDs(ID, waId)

            # self.logger.info("WA Message send to %s with ID %s", buddy, waId)

    def executeCommand(self, command, room):
        if command == "\\leave":
            self.logger.debug("Leaving room %s", room)
            self.leaveGroup(room)  # Leave group on whatsapp side
            group = self.groups[room]
            group.leaveRoom()  # Delete Room on spectrum side
            del self.groups[room]

    def _requestLastSeen(self, buddy):
        def onSuccess(buddy, lastseen):
            timestamp = time.localtime(time.localtime() - lastseen)
            timestring = time.strftime("%a, %d %b %Y %H:%M:%S", timestamp)
            self.sendMessageToXMPP(
                buddy, "%s (%s) %s" % (timestring, ago(lastseen), str(lastseen))
            )

        def onError(errorIqEntity, originalIqEntity):
            self.sendMessageToXMPP(errorIqEntity.getFrom(), "LastSeen Error")

        self.requestLastSeen(buddy, onSuccess, onError)

    def _sendLocation(self, buddy, message, ID):
        latitude, longitude = message.split(":")[1].split(",")
        waId = self.sendLocation(buddy, float(latitude), float(longitude))
        self.msgIDs[waId] = MsgIDs(ID, waId)
        self.logger.info("WA Location Message send to %s with ID %s", buddy, waId)

    def sendMessageToXMPP(self, buddy, message, timestamp="", nickname=""):
        if timestamp:
            timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

        if self.initialized == False:
            self.logger.debug(
                "Message queued from %s to %s: %s" % (buddy, self.legacyName, message)
            )
            self.offlineQueue.append((buddy, message, timestamp))
        else:
            self.logger.debug(
                "Message sent from %s to %s: %s" % (buddy, self.legacyName, message)
            )
            self.backend.handle_message(self.user, buddy, message, "", "", timestamp)

    def sendGroupMessageToXMPP(
        self, room, number, messageContent, timestamp="", defaultname=""
    ):
        if timestamp:
            timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))

        if self.initialized == False:
            self.logger.debug(
                "Group message queued from %s to %s: %s"
                % (number, room, messageContent)
            )

            if room not in self.groupOfflineQueue:
                self.groupOfflineQueue[room] = []

            self.groupOfflineQueue[room].append((number, messageContent, timestamp))
        else:
            self.logger.debug(
                "Group message sent from %s to %s: %s" % (number, room, messageContent)
            )
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
                    self.backend.handleMessage(
                        self.user, room, messageContent, nick, "", timestamp
                    )
                else:
                    self.bot.send(
                        "You have received a message in group: %s@%s"
                        % (room, self.backend.spectrum_jid)
                    )
                    self.bot.send("Join the group in order to reply")
                    self.bot.send("%s: %s" % (nick, messageContent))
            except KeyError:
                self.logger.warn("Group is not in group list")
                self.backend.handleMessage(
                    self.user,
                    self._shortenGroupId(room),
                    messageContent,
                    number,
                    "",
                    timestamp,
                )

    def changeStatus(self, status):
        if status != self.status:
            self.logger.info("Status changed: %s" % status)
            self.status = status

            if (
                status == spectrum2.protocol_pb2.STATUS_ONLINE
                or status == spectrum2.protocol_pb2.STATUS_FFC
            ):
                self.sendPresence(True)
            else:
                self.sendPresence(False)

    def changeStatusMessage(self, statusMessage):
        if (statusMessage != self.statusMessage) or (self.initialized == False):
            self.statusMessage = statusMessage
            self.setStatus(statusMessage)
            self.logger.info("Status message changed: %s" % statusMessage)

            # if self.initialized == False:
            #    self.sendOfflineMessages()
            #    self.bot.call("welcome")
            #    self.initialized = True

    def sendOfflineMessages(self):
        # Flush Queues
        while self.offlineQueue:
            msg = self.offlineQueue.pop(0)
            self.backend.handleMessage(self.user, msg[0], msg[1], "", "", msg[2])

    # Called when user logs in to initialize the roster
    def loadBuddies(self, buddies):
        self.buddies.load(buddies)

    # also for adding a new buddy
    def updateBuddy(self, buddy, nick, groups, image_hash=None):
        if buddy != "bot":
            self.buddies.update(buddy, nick, groups, image_hash)

    def removeBuddy(self, buddy):
        if buddy != "bot":
            self.logger.info("Buddy removed: %s" % buddy)
            self.buddies.remove(buddy)

    def requestVCard(self, buddy, ID=None):
        self.buddies.requestVCard(buddy, ID)

    def createThumb(self, size=100, raw=False):
        img = Image.open(self.imgPath)
        width, height = img.size
        img_thumbnail = self.imgPath + "_thumbnail"

        if width > height:
            nheight = float(height) / width * size
            nwidth = size
        else:
            nwidth = float(width) / height * size
            nheight = size

        img.thumbnail((nwidth, nheight), Image.ANTIALIAS)
        img.save(img_thumbnail, "JPEG")

        with open(img_thumbnail, "rb") as imageFile:
            raw = base64.b64encode(imageFile.read())

        return raw

    # Not used
    def onLocationReceived(
        self,
        messageId,
        jid,
        name,
        preview,
        latitude,
        longitude,
        receiptRequested,
        isBroadcast,
    ):
        buddy = jid.split("@")[0]
        self.logger.info(
            "Location received from %s: %s, %s" % (buddy, latitude, longitude)
        )

        url = "http://maps.google.de?%s" % urllib.urlencode(
            {"q": "%s %s" % (latitude, longitude)}
        )
        self.sendMessageToXMPP(buddy, utils.shorten(url))
        if receiptRequested:
            self.call("message_ack", (jid, messageId))

    def onGroupSubjectReceived(
        self, messageId, gjid, jid, subject, timestamp, receiptRequested
    ):
        room = gjid.split("@")[0]
        buddy = jid.split("@")[0]

        self.backend.handleSubject(self.user, room, subject, buddy)
        if receiptRequested:
            self.call("subject_ack", (gjid, messageId))

    # Yowsup Notifications
    def onGroupParticipantRemoved(
        self, gjid, jid, author, timestamp, messageId, receiptRequested
    ):
        room = gjid.split("@")[0]
        buddy = jid.split("@")[0]

        self.logger.info("Removed %s from room %s" % (buddy, room))

        self.backend.handleParticipantChanged(
            self.user,
            buddy,
            room,
            spectrum2.protocol_pb2.PARTICIPANT_FLAG_NONE,
            spectrum2.protocol_pb2.STATUS_NONE,
        )  # TODO

        if receiptRequested:
            self.call("notification_ack", (gjid, messageId))

    def onContactProfilePictureUpdated(
        self, jid, timestamp, messageId, pictureId, receiptRequested
    ):
        # TODO
        if receiptRequested:
            self.call("notification_ack", (jid, messageId))

    def onGroupPictureUpdated(
        self, jid, author, timestamp, messageId, pictureId, receiptRequested
    ):
        # TODO
        if receiptRequested:
            self.call("notification_ack", (jid, messageId))
