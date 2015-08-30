
from yowsup import env
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent, YowParallelLayer

# Layers
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

class YowsupApp(object):
	def __init__(self):
		env.CURRENT_ENV = env.S40YowsupEnv()

		layers = (SpectrumLayer,
				YowParallelLayer((YowAuthenticationProtocolLayer,
					YowMessagesProtocolLayer,
					YowReceiptProtocolLayer,
					YowAckProtocolLayer,
					YowMediaProtocolLayer,
					YowIbProtocolLayer,
					YowIqProtocolLayer,
					YowNotificationsProtocolLayer,
					YowContactsIqProtocolLayer,
#					 YowChatstateProtocolLayer,
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
		try:
			self.stack.loop(timeout=0.5, discrete=0.5)
		except AuthError as e: # For some reason Yowsup throws an exception
			self.onAuthFailure("%s" % e)

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
		self.stack.toLower(receipt)

	def sendTextMessage(self, to, message):
		"""
		Sends a text message

		Args:
			- to: (xxxxxxxxxx@s.whatsapp.net) who to send the message to
			- message: (str) the body of the message
		"""
		messageEntity = TextMessageProtocolEntity(message, to = to)
		self.stack.toLower(messageEntity)

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

	def onDisconnect(self):
		"""
		Called when disconnected from whatsapp
		"""

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback

class YowsupAppLayer(YowInterfaceLayer):
	EVENT_START = 'transwhat.event.SpectrumLayer.start'

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
		self.toLower(notification.ack())
	
	@ProtocolEntityCallback("message")
	def onMessageReceived(self, entity):
		self.caller.onMessage(entity)
