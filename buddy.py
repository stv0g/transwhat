__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2015, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"

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

from Spectrum2 import protocol_pb2

import logging
import time
import utils
import base64

import deferred
from deferred import call


class Buddy():
	def __init__(self, owner, number, nick, statusMsg, groups, image_hash):
		self.nick = nick
		self.owner = owner
		self.number = number
		self.groups = groups
		self.image_hash = image_hash if image_hash is not None else ""
		self.statusMsg = u""
		self.lastseen = 0
		self.presence = 0

	def update(self, nick, groups, image_hash):
		self.nick = nick
		self.groups = groups
		if image_hash is not None:
			self.image_hash = image_hash

	def __str__(self):
		return "%s (nick=%s)" % (self.number, self.nick)

class BuddyList(dict):

	def __init__(self, owner, backend, user, session):
		self.owner = owner
		self.backend = backend
		self.session = session
		self.user = user
		self.logger = logging.getLogger(self.__class__.__name__)
		self.synced = False

	def _load(self, buddies):
		for buddy in buddies:
			number = buddy.buddyName
			nick = buddy.alias
			statusMsg = buddy.statusMessage.decode('utf-8')
			groups = [g for g in buddy.group]
			image_hash = buddy.iconHash
			self[number] = Buddy(self.owner, number, nick, statusMsg,
					groups, image_hash)

		self.logger.debug("Update roster")

		contacts = self.keys()
		contacts.remove('bot')

		if self.synced == False:
			self.session.sendSync(contacts, delta = False, interactive = True)
			self.synced = True

		self.logger.debug("Roster add: %s", str(list(contacts)))

		for number in contacts:
			buddy = self[number]
			self.backend.handleBuddyChanged(self.user, number, buddy.nick,
				buddy.groups, protocol_pb2.STATUS_NONE,
				iconHash = buddy.image_hash if buddy.image_hash is not None else "")
			self.session.subscribePresence(number)
		self.logger.debug("%s is requesting statuses of: %s", self.user, contacts)
		self.session.requestStatuses(contacts, success = self.onStatus)

	def onStatus(self, contacts):
		self.logger.debug("%s received statuses of: %s", self.user, contacts)
		for number, (status, time) in contacts.iteritems():
			buddy = self[number]
			if status is None:
				buddy.statusMsg = ""
			else:
				buddy.statusMsg = utils.softToUni(status)
			self.updateSpectrum(buddy)


	def load(self, buddies):
		if self.session.loggedIn:
			self._load(buddies)
		else:
			self.session.loginQueue.append(lambda: self._load(buddies))

	def update(self, number, nick, groups, image_hash):
		if number in self:
			buddy = self[number]
			buddy.update(nick, groups, image_hash)
		else:
			buddy = Buddy(self.owner, number, nick, "",  groups, image_hash)
			self[number] = buddy
			self.logger.debug("Roster add: %s", buddy)
			self.session.sendSync([number], delta = True, interactive = True)
			self.session.subscribePresence(number)
			self.session.requestStatuses([number], success = self.onStatus)
			if image_hash == "" or image_hash is None:
				self.requestVCard(number)
		self.updateSpectrum(buddy)
		return buddy

	def updateSpectrum(self, buddy):
		if buddy.presence == 0:
			status = protocol_pb2.STATUS_NONE
		elif buddy.presence == 'unavailable':
			status = protocol_pb2.STATUS_AWAY
		else:
			status = protocol_pb2.STATUS_ONLINE

		statusmsg = buddy.statusMsg
		if buddy.lastseen != 0:
			timestamp = time.localtime(buddy.lastseen)
			statusmsg += time.strftime("\n Last seen: %a, %d %b %Y %H:%M:%S", timestamp)

		iconHash = buddy.image_hash if buddy.image_hash is not None else ""

		self.logger.debug("Updating buddy %s (%s) in %s, image_hash = %s",
				buddy.nick, buddy.number, buddy.groups, iconHash)
		self.logger.debug("Status Message: %s", statusmsg)
		self.backend.handleBuddyChanged(self.user, buddy.number, buddy.nick,
			buddy.groups, status, statusMessage=statusmsg, iconHash=iconHash)


	def remove(self, number):
		try:
			buddy = self[number]
			del self[number]
			self.backend.handleBuddyChanged(self.user, number, "", [],
											protocol_pb2.STATUS_NONE)
			self.backend.handleBuddyRemoved(self.user, number)
			self.session.unsubscribePresence(number)
#			TODO Sync remove
			return buddy
		except KeyError:
			return None

	def requestVCard(self, buddy, ID=None):
		if buddy == self.user or buddy == self.user.split('@')[0]:
			buddy = self.session.legacyName

		# Get profile picture
		self.logger.debug('Requesting profile picture of %s', buddy)
		response = deferred.Deferred()
		self.session.requestProfilePicture(buddy, onSuccess = response.run)
		response = response.arg(0)

		pictureData = response.pictureData()
		# Send VCard
		if ID != None:
			call(self.logger.debug, 'Sending VCard (%s) with image id %s: %s',
					ID, response.pictureId(), pictureData.then(base64.b64encode))
			call(self.backend.handleVCard, self.user, ID, buddy, "", "",
					pictureData)

		# Send image hash
		if not buddy == self.session.legacyName:
			try:
				obuddy = self[buddy]
				nick = obuddy.nick
				groups = obuddy.groups
			except KeyError:
				nick = ""
				groups = []
			image_hash = pictureData.then(utils.sha1hash)
			call(self.logger.debug, 'Image hash is %s', image_hash)
			call(self.update, buddy, nick, groups, image_hash)
