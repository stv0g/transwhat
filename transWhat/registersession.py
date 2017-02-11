# use unicode encoding for all literals by default (for python2.x)
from __future__ import unicode_literals

__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2015-2017, Steffen Vogel"
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

from yowsupwrapper import YowsupApp
import logging
import threadutils
import sys

class RegisterSession(YowsupApp):
	"""
	A dummy Session object that is used to register a user to whatsapp
	"""
	WANT_CC = 0
	WANT_SMS = 1
	def __init__(self, backend, user, legacyName, extra):
		self.user = user
		self.number = legacyName
		self.backend = backend
		self.countryCode = ''
		self.logger = logging.getLogger(self.__class__.__name__)
		self.state = self.WANT_CC

	def login(self, password=""):
		self.backend.handleConnected(self.user)
		self.backend.handleBuddyChanged(self.user, 'bot', 'bot',
				['Admin'], protocol_pb2.STATUS_ONLINE)
		self.backend.handleMessage(self.user, 'bot',
				'Please enter your country code')

	def sendMessageToWA(self, buddy, message, ID='', xhtml=''):
		if buddy == 'bot' and self.state == self.WANT_CC:
			try:
				country_code = int(message.strip())
			except ValueError:
				self.backend.handleMessage(self.user, 'bot',
						'Country code must be a number')
			else: # Succeded in decoding country code
				country_code = "%s" % country_code
				if country_code != self.number[:len(country_code)]:
					self.backend.handleMessage(self.user,
							'bot', 'Number does not start with provided country code')
				else:
					self.backend.handleMessage(self.user, 'bot', 'Requesting sms code')
					self.logger.debug('Requesting SMS code for %s' % self.user)
					self.countryCode = country_code
					self._requestSMSCodeNonBlock()
		elif buddy == 'bot' and self.state == self.WANT_SMS:
			code = message.strip()
			if self._checkSMSFormat(code):
				self._requestPassword(code)
			else:
				self.backend.handleMessage(self.user,
						'bot', 'Invalid code. Must be of the form XXX-XXX.')
		else:
			self.logger.warn('Unauthorised user (%s) attempting to send messages' %
					self.user)
			self.backend.handleMessage(self.user, buddy,
			'You are not logged in yet. You can only send messages to bot.')

	def _checkSMSFormat(self, sms):
		splitting = sms.split('-')
		if len(splitting) != 2:
			return False
		a, b = splitting
		if len(a) != 3 and len(b) != 3:
			return False
		try:
			int(a)
			int(b)
		except ValueError:
			return False
		return True

	def _requestSMSCodeNonBlock(self):
		number = self.number[len(self.countryCode):]
		threadFunc = lambda: self.requestSMSCode(self.countryCode, number)
		threadutils.runInThread(threadFunc, self._confirmation)
		self.backend.handleMessage(self.user, 'bot', 'SMS Code Sent')

	def _confirmation(self, result):
		self.state = self.WANT_SMS
		resultStr = self._resultToString(result)
		self.backend.handleMessage(self.user, 'bot', 'Response:')
		self.backend.handleMessage(self.user, 'bot', resultStr)
		self.backend.handleMessage(self.user, 'bot', 'Please enter SMS Code')

	def _requestPassword(self, smsCode):
		cc = self.countryCode
		number = self.number[len(cc):]
		threadFunc = lambda: self.requestPassword(cc, number, smsCode)
		threadutils.runInThread(threadFunc, self._gotPassword)
		self.backend.handleMessage(self.user, 'bot', 'Getting Password')

	def _gotPassword(self, result):
		resultStr = self._resultToString(result)
		self.backend.handleMessage(self.user, 'bot', 'Response:')
		self.backend.handleMessage(self.user, 'bot', resultStr)
		self.backend.handleMessage(self.user, 'bot', 'Logging you in')
		password = result['pw']
		self.backend.relogin(self.user, self.number, password, None)

	def _resultToString(self, result):
		unistr = str if sys.version_info >= (3, 0) else unicode
		out = []
		for k, v in result.items():
			if v is None:
				continue
			out.append("%s: %s" % (k, v))

		return "\n".join(out)

	# Dummy methods. Whatsapp backend might call these, but they should have no
	# effect
	def logout(self):
		pass

	def joinRoom(self, room, nickname):
		pass

	def leaveRoom(self, room):
		pass

	def changeStatusMessage(self, statusMessage):
		pass

	def changeStatus(self, status):
		pass

	def loadBuddies(self, buddies):
		pass

	def updateBuddy(self, buddies):
		pass

	def removeBuddy(self, buddies):
		pass

	def sendTypingStarted(self, buddy):
		pass

	def sendTypingStopped(self, buddy):
		pass

	def requestVCard(self, buddy, ID):
		pass

	def setProfilePicture(self, previewPicture, fullPicture = None):
		pass
