
from yowsup import env
from yowsup.stacks import YowStack

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

class YowsupApp:
	def __init__(self):
		self.logged_in = False

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
	def onAck(self, entity)
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
