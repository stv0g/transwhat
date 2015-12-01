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

from Spectrum2 import protocol_pb2

import logging


class Buddy():
	def __init__(self, owner, number, nick, statusMsg, groups, image_hash):
		self.nick = nick
		self.owner = owner
		self.number = number
		self.groups = groups
		self.image_hash = image_hash if image_hash is not None else ""
		self.statusMsg = ""
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

	def load(self, buddies):
		for buddy in buddies:
			number = buddy.buddyName
			nick = buddy.alias
			statusMsg = buddy.statusMessage
			groups = [g for g in buddy.group]
			image_hash = buddy.iconHash
			self[number] = Buddy(self.owner, number, nick, statusMsg,
					groups, image_hash)
		self.logger.debug("Update roster")

#		old = self.buddies.keys()
#		self.buddies.load()
#		new = self.buddies.keys()
#		contacts = new
		contacts = self.keys()

		if self.synced == False:
			self.session.sendSync(contacts, delta = False, interactive = True)
			self.synced = True

#		add = set(new) - set(old)
#		remove = set(old) - set(new)

#		self.logger.debug("Roster remove: %s", str(list(remove)))
		self.logger.debug("Roster add: %s", str(list(contacts)))

#		for number in remove:
#			self.backend.handleBuddyChanged(self.user, number, "", [],
#											protocol_pb2.STATUS_NONE)
#			self.backend.handleBuddyRemoved(self.user, number)
#			self.unsubscribePresence(number)
#
		for number in contacts:
			self.session.subscribePresence(number)
			buddy = self[number]
			self.backend.handleBuddyChanged(self.user, number, buddy.nick,
				buddy.groups, protocol_pb2.STATUS_NONE,
				iconHash = buddy.image_hash if buddy.image_hash is not None else "")


	def update(self, number, nick, groups, image_hash):
		if number in self:
			buddy = self[number]
			buddy.update(nick, groups, image_hash)
		else:
			self.session.sendSync([number], delta = True, interactive = True)
			self.session.subscribePresence(number)
			buddy = Buddy(self.owner, number, nick, "",  groups, image_hash)
			self[number] = buddy
			self.logger.debug("Roster add: %s", buddy)

		self.backend.handleBuddyChanged(self.user, number, buddy.nick,
			buddy.groups, protocol_pb2.STATUS_NONE,
			iconHash = buddy.image_hash if buddy.image_hash is not None else "")

		return buddy

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
