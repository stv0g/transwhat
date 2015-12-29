__author__ = u"Steffen Vogel"
__copyright__ = u"Copyright 2015, Steffen Vogel"
__license__ = u"GPLv3"
__maintainer__ = u"Steffen Vogel"
__email__ = u"post@steffenvogel.de"

u"""
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

class Group():

	def __init__(self, id, owner, subject, subjectOwner, backend, user):
		self.id = id
		self.subject = subject
		self.subjectOwner = subjectOwner
		self.owner = owner
		self.joined = False
		self.backend = backend
		self.user = user

		self.nick = u"me"
		# Participants is a number -> nickname dict
		self.participants = {}

	def addParticipants(self, participants, buddies, yourNumber):
		u"""
		Adds participants to the group.

		Args:
			- participants: (Iterable) phone numbers of participants
			- buddies: (dict) Used to get the nicknames of the participants
			- yourNumber: The number you are using
		"""
		for jid in participants:
			number = jid.split(u'@')[0]
			try:
				nick = buddies[number].nick
			except KeyError:
				nick = number
			if number == yourNumber:
				nick = self.nick
			if nick == u"":
				nick = number
			self.participants[number] = nick

	def sendParticipantsToSpectrum(self, yourNumber):
		for number, nick in self.participants.iteritems():
			if number == self.owner:
				flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
			else:
				flags = protocol_pb2.PARTICIPANT_FLAG_NONE
			if number == yourNumber:
				flags = flags | protocol_pb2.PARTICIPANT_FLAG_ME

			self._updateParticipant(number, flags, protocol_pb2.STATUS_ONLINE)

	def removeParticipants(self, participants):
		for jid in participants:
			number = jid.split(u'@')[0]
			nick = self.participants[number]
			flags = protocol_pb2.PARTICIPANT_FLAG_NONE
			self._updateParticipant(number, flags, protocol_pb2.STATUS_NONE)
			del self.participants[number]

	def changeNick(self, number, new_nick):
		if self.participants[number] == new_nick:
			return
		if number == self.owner:
			flags = protocol_pb2.PARTICIPANT_FLAG_MODERATOR
		else:
			flags = protocol_pb2.PARTICIPANT_FLAG_NONE
		self._updateParticipant(number, flags, protocol_pb2.STATUS_ONLINE, new_nick)
		self.participants[number] = new_nick

	def _updateParticipant(self, number, flags, status, newNick = u""):
		nick = self.participants[number]
		# Notice the status message is the buddy's number
		if self.joined:
			self.backend.handleParticipantChanged(
					self.user, nick, self.id, flags,
					status, number, newname = newNick)
