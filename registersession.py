from Spectrum2 import protocol_pb2

from yowsupwrapper import YowsupApp
import logging
import threadutils

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
				country_code = str(country_code)
				if country_code != self.number[:len(country_code)]:
					self.backend.handleMessage(self.user,
							'bot', 'Number does not start with provided country code')
				else:
					self.backend.handleMessage(self.user, 'bot', 'Requesting sms code')
					self.logger.debug('Requesting SMS code for %s', self.user)
					self._requestSMSCodeNonBlock(country_code)
		elif buddy == 'bot' and self.state == self.WANT_SMS:
			self.backend.handleMessage(self.user, 'bot', 'Not implemented')
		else:
			self.logger.warn('Unauthorised user (%s) attempting to send messages',
					self.user)
			self.backend.handleMessage(self.user, buddy,
			'You are not logged in yet. You can only send messages to bot.')

	def _requestSMSCodeNonBlock(self, country_code):
		number = self.number[len(country_code):]
		threadFunc = lambda: self.requestSMSCode(country_code, number)
		threadutils.runInThread(threadFunc, self._confirmation)

	def _confirmation(self, result):
		self.backend.handleMessage(self.user, 'bot', 'SMS Code Sent')
		self.state = self.WANT_SMS
		self.backend.handleMessage(self.user, 'bot', 'Please enter SMS Code')

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
