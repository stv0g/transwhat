
from yowsup import env
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent, YowParallelLayer
from yowsup.layers.auth import AuthError

# Layers
from yowsup.layers.axolotl					   import YowAxolotlLayer
from yowsup.layers.auth						   import YowCryptLayer, YowAuthenticationProtocolLayer
from yowsup.layers.coder					   import YowCoderLayer
from yowsup.layers.logger					   import YowLoggerLayer
from yowsup.layers.network					   import YowNetworkLayer
from yowsup.layers.protocol_messages		   import YowMessagesProtocolLayer
from yowsup.layers.stanzaregulator			   import YowStanzaRegulator
from yowsup.layers.protocol_media			   import YowMediaProtocolLayer
from yowsup.layers.protocol_acks			   import YowAckProtocolLayer
from yowsup.layers.protocol_receipts		   import YowReceiptProtocolLayer
from yowsup.layers.protocol_groups			   import YowGroupsProtocolLayer
from yowsup.layers.protocol_presence		   import YowPresenceProtocolLayer
from yowsup.layers.protocol_ib				   import YowIbProtocolLayer
from yowsup.layers.protocol_notifications	   import YowNotificationsProtocolLayer
from yowsup.layers.protocol_iq				   import YowIqProtocolLayer
from yowsup.layers.protocol_contacts		   import YowContactsIqProtocolLayer
from yowsup.layers.protocol_chatstate		   import YowChatstateProtocolLayer
from yowsup.layers.protocol_privacy			   import YowPrivacyProtocolLayer
from yowsup.layers.protocol_profiles		   import YowProfilesProtocolLayer
from yowsup.layers.protocol_calls import YowCallsProtocolLayer

# ProtocolEntities

from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_acks.protocolentities	 import *
from yowsup.layers.protocol_receipts.protocolentities  import *

class YowsupApp(object):
	def __init__(self):
		env.CURRENT_ENV = env.S40YowsupEnv()

		layers = (YowsupAppLayer,
				YowParallelLayer((YowAuthenticationProtocolLayer,
					YowMessagesProtocolLayer,
					YowReceiptProtocolLayer,
					YowAckProtocolLayer,
					YowMediaProtocolLayer,
					YowIbProtocolLayer,
					YowIqProtocolLayer,
					YowNotificationsProtocolLayer,
					YowContactsIqProtocolLayer,
					YowChatstateProtocolLayer,
					YowCallsProtocolLayer,
					YowMediaProtocolLayer,
					YowPrivacyProtocolLayer,
					YowProfilesProtocolLayer,
					YowGroupsProtocolLayer,
					YowPresenceProtocolLayer)),
				YowAxolotlLayer,
				YowCoderLayer,
				YowCryptLayer,
				YowStanzaRegulator,
				YowNetworkLayer
		)
		self.stack = YowStack(layers)
		self.stack.broadcastEvent(
			YowLayerEvent(YowsupAppLayer.EVENT_START, caller = self)
		)

	def login(self, username, password):
		"""Login to yowsup

		Should result in onAuthSuccess or onAuthFailure to be called.

		Args:
			- username: (str) username in the form of 1239482382 (country code
				  and cellphone number)

			- password: (str) base64 encoded password
		  """
		self.stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS,
							(username, password))
		self.stack.setProp(YowNetworkLayer.PROP_ENDPOINT,
							YowConstants.ENDPOINTS[0])
		self.stack.setProp(YowCoderLayer.PROP_DOMAIN,
							YowConstants.DOMAIN)
		self.stack.setProp(YowCoderLayer.PROP_RESOURCE,
							env.CURRENT_ENV.getResource())
#		self.stack.setProp(YowIqProtocolLayer.PROP_PING_INTERVAL, 5)

		try:
			self.stack.broadcastEvent(
					YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
		except TypeError as e: # Occurs when password is not correctly formated
			self.onAuthFailure('password not base64 encoded')
#		try:
#			self.stack.loop(timeout=0.5, discrete=0.5)
#		except AuthError as e: # For some reason Yowsup throws an exception
#			self.onAuthFailure("%s" % e)

	def logout(self):
		"""
		Logout from whatsapp
		"""
		self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
	
	def sendReceipt(self, _id, _from, read, participant):
		"""
		Send a receipt (delivered: double-tick, read: blue-ticks)

		Args:
			- _id: id of message received
			- _from
			- read: ('read' or something else)
			- participant
		"""
		receipt = OutgoingReceiptProtocolEntity(_id, _from, read, participant)
		self.sendEntity(receipt)

	def sendTextMessage(self, to, message):
		"""
		Sends a text message

		Args:
			- to: (xxxxxxxxxx@s.whatsapp.net) who to send the message to
			- message: (str) the body of the message
		"""
		messageEntity = TextMessageProtocolEntity(message, to = to)
		self.sendEntity(messageEntity)

	def sendPresence(self, available):
		"""
		Send presence to whatsapp

		Args:
			- available: (boolean) True if available false otherwise
		"""
		if available:
			self.sendEntity(AvailablePresenceProtocolEntity())
		else:
			self.sendEntity(UnavailablePresenceProtocolEntity())

	def subscribePresence(self, phone_number):
		"""
		Subscribe to presence updates from phone_number

		Args:
			- phone_number: (str) The cellphone number of the person to
				subscribe to
		"""
		jid = phone_number + '@s.whatsapp.net'
		entity = SubscribePresenceProtocolEntity(jid)
		self.sendEntity(entity)

	def unsubscribePresence(self, phone_number):
		"""
		Unsubscribe to presence updates from phone_number

		Args:
			- phone_number: (str) The cellphone number of the person to
				unsubscribe from
		"""
		jid = phone_number + '@s.whatsapp.net'
		entity = UnsubscribePresenceProtocolEntity(jid)
		self.sendEntity(entity)
	
	def setStatus(self, statusText):
		"""
		Send status to whatsapp

		Args:
			- statusTest: (str) Your whatsapp status
		"""
		entity = PresenceProtocolEntity(name = statusText if len(statusText) == 0 else 'this')
		self.sendEntity(entity)
	
	def sendTyping(self, phoneNumber, typing):
		"""
		Notify buddy using phoneNumber that you are typing to him

		Args:
			- phoneNumber: (str) cellphone number of the buddy you are typing to.
			- typing: (bool) True if you are typing, False if you are not
		"""
		jid = phoneNumber + '@s.whatsapp.net'
		if typing:
			state = OutgoingChatstateProtocolEntity(
				ChatstateProtocolEntity.STATE_TYPING, jid
			)
		else:
			state = OutgoingChatstateProtocolEntity(
				ChatstateProtocolEntity.STATE_PAUSED, jid
			)
		self.sendEntity(state)
	
	def requestLastSeen(self, phoneNumber, success = None, failure = None):
		"""
		Requests when user was last seen.
		Args:
			- phone_number: (str) the phone number of the user
			- success: (func) called when request is successfully processed.
				The first argument is the number, second argument is the seconds
				since last seen.
			- failure: (func) called when request has failed
		"""
		iq = LastseenIqProtocolEntity(phoneNumber + '@s.whatsapp.net')
		self.stack.broadcastEvent(
			YowLayerEvent(YowsupAppLayer.SEND_IQ,
				iq = iq,
				success = self._lastSeenSuccess(success),
				failure = failure,
				)
		)
	def _lastSeenSuccess(self, success):
		def func(response, request):
			success(response._from.split('@')[0], response.seconds)
		return func

	def onAuthSuccess(self, status, kind, creation, expiration, props, nonce, t):
		"""
		Called when login is successful.

		Args:
			- status
			- kind
			- creation
			- expiration
			- props
			- nonce
			- t
		"""
		pass

	def onAuthFailure(self, reason):
		"""
		Called when login is a failure

		Args:
			- reason: (str) Reason for the login failure
		"""
		pass

	def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
		"""
		Called when a receipt is received (double tick or blue tick)

		Args
			- _id
			- _from
			- timestamp
			- type: Is 'read' for blue ticks and None for double-ticks
			- participant: (dxxxxxxxxxx@s.whatsapp.net) delivered to or
				read by this participant in group
			- offline: (True, False or None)
			- items
		"""
		pass

	def onAck(self, _id,_class, _from, timestamp):
		"""
		Called when Ack is received

		Args:
			- _id
			- _class: ('message', 'receipt' or something else?)
			- _from
			- timestamp
		"""
		pass
	
	def onPresenceReceived(self, _type, name, _from, last):
		"""
		Called when presence (e.g. available, unavailable) is received
		from whatsapp

		Args:
			- _type: (str) 'available' or 'unavailable'
			- _name
			- _from
			- _last
		"""
		pass

	def onDisconnect(self):
		"""
		Called when disconnected from whatsapp
		"""
	
	def onContactTyping(self, number):
		"""
		Called when contact starts to type

		Args:
			- number: (str) cellphone number of contact
		"""
		pass

	def onContactPaused(self, number):
		"""
		Called when contact stops typing

		Args:
			- number: (str) cellphone number of contact
		"""
		pass

	def sendEntity(self, entity):
		"""Sends an entity down the stack (as if YowsupAppLayer called toLower)"""
		self.stack.broadcastEvent(YowLayerEvent(YowsupAppLayer.TO_LOWER_EVENT,
			entity = entity
		))

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback

class YowsupAppLayer(YowInterfaceLayer):
	EVENT_START = 'transwhat.event.YowsupAppLayer.start'
	TO_LOWER_EVENT = 'transwhat.event.YowsupAppLayer.toLower'
	SEND_IQ = 'transwhat.event.YowsupAppLayer.sendIq'

	def onEvent(self, layerEvent):
		# We cannot pass instance varaibles in through init, so we use an event
		# instead
		# Return False if you want the event to propogate down the stack
		# return True otherwise
		if layerEvent.getName() == YowsupAppLayer.EVENT_START:
			self.caller = layerEvent.getArg('caller')
			return True
		elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
			self.caller.onDisconnect()
			return True
		elif layerEvent.getName() == YowsupAppLayer.TO_LOWER_EVENT:
			self.toLower(layerEvent.getArg('entity'))
			return True
		elif layerEvent.getName() == YowsupAppLayer.SEND_IQ:
			iq = layerEvent.getArg('iq')
			success = layerEvent.getArg('success')
			failure = layerEvent.getArg('failure')
			self._sendIq(iq, success, failure)
			return True
		return False

	@ProtocolEntityCallback('success')
	def onAuthSuccess(self, entity):
		# entity is SuccessProtocolEntity
		status = entity.status
		kind = entity.kind
		creation = entity.creation
		expiration = entity.expiration
		props = entity.props
		nonce = entity.nonce
		t = entity.t # I don't know what this is
		self.caller.onAuthSuccess(status, kind, creation, expiration, props, nonce, t)

	@ProtocolEntityCallback('failure')
	def onAuthFailure(self, entity):
		# entity is FailureProtocolEntity
		reason = entity.reason
		self.caller.onAuthFailure(reason)

	@ProtocolEntityCallback('receipt')
	def onReceipt(self, entity):
		"""Sends ack automatically"""
		# entity is IncomingReceiptProtocolEntity
		ack = OutgoingAckProtocolEntity(entity.getId(),
				'receipt', entity.getType(), entity.getFrom())
		self.toLower(ack)
		_id = entity._id
		_from = entity._from
		timestamp = entity.timestamp
		type = entity.type
		participant = entity.participant
		offline = entity.offline
		items = entity.items
		self.caller.onReceipt(_id, _from, timestamp, type, participant, offline, items)

	@ProtocolEntityCallback('ack')
	def onAck(self, entity):
		# entity is IncomingAckProtocolEntity
		self.caller.onAck(
			entity._id,
			entity._class,
			entity._from,
			entity.timestamp
		)

	@ProtocolEntityCallback('notification')
	def onNotification(self, entity):
		"""
		Sends ack automatically
		"""
		self.toLower(entity.ack())
	
	@ProtocolEntityCallback('message')
	def onMessageReceived(self, entity):
		self.caller.onMessage(entity)

	@ProtocolEntityCallback('presence')
	def onPresenceReceived(self, presence):
		_type = presence.getType()
		name = presence.getName()
		_from = presence.getFrom()
		last = presence.getLast()
		self.caller.onPresenceReceived(_type, name, _from, last)
	
	@ProtocolEntityCallback('chatstate')
	def onChatstate(self, chatstate):
		number = chatstate._from.split('@')[0]
		if chatstate.getState() == ChatstateProtocolEntity.STATE_TYPING:
			self.caller.onContactTyping(number)
		else:
			self.caller.onContactPaused(number)
