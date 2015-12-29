import logging

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

from yowsup.layers.protocol_acks.protocolentities import *
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_contacts.protocolentities import *
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities  import *
from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_profiles.protocolentities import *
from yowsup.layers.protocol_receipts.protocolentities  import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader

from functools import partial

#from session import MsgIDs

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
		self.logger = logging.getLogger(self.__class__.__name__)
		self.stack = YowStack(layers)
		self.stack.broadcastEvent(
			YowLayerEvent(YowsupAppLayer.EVENT_START, caller = self)
		)

	def login(self, username, password):
		u"""Login to yowsup

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
			self.onAuthFailure(u'password not base64 encoded')
#		try:
#			self.stack.loop(timeout=0.5, discrete=0.5)
#		except AuthError as e: # For some reason Yowsup throws an exception
#			self.onAuthFailure(u"%s" % e)

	def logout(self):
		u"""
		Logout from whatsapp
		"""
		self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))

	def sendReceipt(self, _id, _from, read, participant):
		u"""
		Send a receipt (delivered: double-tick, read: blue-ticks)

		Args:
			- _id: id of message received
			- _from: jid of person who sent the message
			- read: ('read' or None) None is just delivered, 'read' is read
			- participant
		"""
		receipt = OutgoingReceiptProtocolEntity(_id, _from, read, participant)
		self.sendEntity(receipt)

	def sendTextMessage(self, to, message):
		u"""
		Sends a text message

		Args:
			- to: (xxxxxxxxxx@s.whatsapp.net) who to send the message to
			- message: (str) the body of the message
		"""
		messageEntity = TextMessageProtocolEntity(message, to = to)
		self.sendEntity(messageEntity)
		return messageEntity.getId()

	def sendLocation(self, to, latitude, longitude):
		messageEntity = LocationMediaMessageProtocolEntity(latitude,longitude, None, None, u"raw", to = to)
		self.sendEntity(messageEntity)
                return messageEntity.getId()

	def image_send(self, jid, path, caption = None):
            	entity = RequestUploadIqProtocolEntity(RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE, filePath=path)
		successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(jid, path, successEntity, originalEntity, caption)
            	errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(jid, path, errorEntity, originalEntity)

            	self.sendIq(entity, successFn, errorFn)

	def onRequestUploadResult(self, jid, filePath, resultRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity, caption = None):

        	if requestUploadIqProtocolEntity.mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            		doSendFn = self._doSendAudio
        	else:
            		doSendFn = self._doSendImage

        	if resultRequestUploadIqProtocolEntity.isDuplicate():
            		doSendFn(filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(), caption)
        	else:
            		successFn = lambda filePath, jid, url: doSendFn(filePath, url, jid, resultRequestUploadIqProtocolEntity.getIp(), caption)
            		mediaUploader = MediaUploader(jid, self.legacyName,  filePath,
                                      resultRequestUploadIqProtocolEntity.getUrl(),
                                      resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                      successFn, self.onUploadError, self.onUploadProgress, async=False)
            		mediaUploader.start()

    	def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
        	self.logger.error(u"Request upload for file %s for %s failed" % (path, jid))

    	def onUploadError(self, filePath, jid, url):
        	#logger.error(u"Upload file %s to %s for %s failed!" % (filePath, url, jid))
		self.logger.error(u"Upload Error!")

    	def onUploadProgress(self, filePath, jid, url, progress):
        	#sys.stdout.write(u"%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        	#sys.stdout.flush()
		pass

	def doSendImage(self, filePath, url, to, ip = None, caption = None):
        	entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption = caption)
        	self.sendEntity(entity)
		#self.msgIDs[entity.getId()] = MsgIDs(self.imgMsgId, entity.getId())
		return entity.getId()


    	def doSendAudio(self, filePath, url, to, ip = None, caption = None):
        	entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        	self.sendEntity(entity)
		#self.msgIDs[entity.getId()] = MsgIDs(self.imgMsgId, entity.getId())
		return entity.getId()



	def sendPresence(self, available):
		u"""
		Send presence to whatsapp

		Args:
			- available: (boolean) True if available false otherwise
		"""
		if available:
			self.sendEntity(AvailablePresenceProtocolEntity())
		else:
			self.sendEntity(UnavailablePresenceProtocolEntity())

	def subscribePresence(self, phone_number):
		u"""
		Subscribe to presence updates from phone_number

		Args:
			- phone_number: (str) The cellphone number of the person to
				subscribe to
		"""
		self.logger.debug(u"Subscribing to Presence updates from %s", (phone_number))
		jid = phone_number + u'@s.whatsapp.net'
		entity = SubscribePresenceProtocolEntity(jid)
		self.sendEntity(entity)

	def unsubscribePresence(self, phone_number):
		u"""
		Unsubscribe to presence updates from phone_number

		Args:
			- phone_number: (str) The cellphone number of the person to
				unsubscribe from
		"""
		jid = phone_number + u'@s.whatsapp.net'
		entity = UnsubscribePresenceProtocolEntity(jid)
		self.sendEntity(entity)

	def leaveGroup(self, group):
		u"""
		Permanently leave a WhatsApp group

		Args:
			- group: (str) the group id (e.g. 27831788123-144024456)
		"""
		entity = LeaveGroupsIqProtocolEntity([group + u'@g.us'])
		self.sendEntity(entity)

	def setStatus(self, statusText):
		u"""
		Send status to whatsapp

		Args:
			- statusTest: (str) Your whatsapp status
		"""
		iq = SetStatusIqProtocolEntity(statusText)
		self.sendIq(iq)
	
	def sendTyping(self, phoneNumber, typing):
		u"""
		Notify buddy using phoneNumber that you are typing to him

		Args:
			- phoneNumber: (str) cellphone number of the buddy you are typing to.
			- typing: (bool) True if you are typing, False if you are not
		"""
		jid = phoneNumber + u'@s.whatsapp.net'
		if typing:
			state = OutgoingChatstateProtocolEntity(
				ChatstateProtocolEntity.STATE_TYPING, jid
			)
		else:
			state = OutgoingChatstateProtocolEntity(
				ChatstateProtocolEntity.STATE_PAUSED, jid
			)
		self.sendEntity(state)
	
	def sendSync(self, contacts, delta = False, interactive = True):
		u"""
		You need to sync new contacts before you interact with
		them, failure to do so could result in a temporary ban.
		
		Args:
			- contacts: ([str]) a list of phone numbers of the
				contacts you wish to sync
			- delta: (bool; default: False) If true only send new
				contacts to sync, if false you should send your full
				contact list.
			- interactive: (bool; default: True) Set to false if you are
				sure this is the first time registering
		"""
		# TODO: Implement callbacks
		mode = GetSyncIqProtocolEntity.MODE_DELTA if delta else GetSyncIqProtocolEntity.MODE_FULL
		context = GetSyncIqProtocolEntity.CONTEXT_INTERACTIVE if interactive else GetSyncIqProtocolEntity.CONTEXT_REGISTRATION
		iq = GetSyncIqProtocolEntity(contacts, mode, context)
		self.sendIq(iq)
	
	def requestStatuses(self, contacts, success = None, failure = None):
		u"""
		Request the statuses of a number of users.

		Args:
			- contacts: ([str]) the phone numbers of users whose statuses you
				wish to request
			- success: (func) called when request is successful
			- failure: (func) called when request has failed
		"""
		iq = GetStatusesIqProtocolEntity([c + u'@s.whatsapp.net' for c in contacts])
		def onSuccess(response, request):
			self.logger.debug(u"Received Statuses %s", response)
			s = {}
			for k, v in response.statuses.iteritems():
				s[k.split(u'@')[0]] = v
			success(s)

		self.sendIq(iq, onSuccess = onSuccess, onError = failure)


	def requestLastSeen(self, phoneNumber, success = None, failure = None):
		u"""
		Requests when user was last seen.
		Args:
			- phone_number: (str) the phone number of the user
			- success: (func) called when request is successfully processed.
				The first argument is the number, second argument is the seconds
				since last seen.
			- failure: (func) called when request has failed
		"""
		iq = LastseenIqProtocolEntity(phoneNumber + u'@s.whatsapp.net')
		self.sendIq(iq, onSuccess = partial(self._lastSeenSuccess, success),
				onError = failure)

	def _lastSeenSuccess(self, success, response, request):
		success(response._from.split(u'@')[0], response.seconds)

	def requestProfilePicture(self, phoneNumber, onSuccess = None, onFailure = None):
		u"""
		Requests profile picture of whatsapp user
		Args:
			- phoneNumber: (str) the phone number of the user
			- onSuccess: (func) called when request is successfully processed.
			- onFailure: (func) called when request has failed
		"""
		iq = GetPictureIqProtocolEntity(phoneNumber + u'@s.whatsapp.net')
		self.sendIq(iq, onSuccess = onSuccess, onError = onFailure)
	
	def requestGroupsList(self, onSuccess = None, onFailure = None):
		iq = ListGroupsIqProtocolEntity()
		self.sendIq(iq, onSuccess = onSuccess, onError = onFailure)

	def requestGroupInfo(self, group, onSuccess = None, onFailure = None):
		u"""
		Request info on a specific group (includes participants, subject, owner etc.)

		Args:
			- group: (str) the group id in the form of xxxxxxxxx-xxxxxxxx
			- onSuccess: (func) called when request is successfully processed.
			- onFailure: (func) called when request is has failed
		"""
		iq = InfoGroupsIqProtocolEntity(group + u'@g.us')
		self.sendIq(iq, onSuccess = onSuccess, onError = onFailure)

	def onAuthSuccess(self, status, kind, creation, expiration, props, nonce, t):
		u"""
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
		u"""
		Called when login is a failure

		Args:
			- reason: (str) Reason for the login failure
		"""
		pass

	def onReceipt(self, _id, _from, timestamp, type, participant, offline, items):
		u"""
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
		u"""
		Called when Ack is received

		Args:
			- _id
			- _class: ('message', 'receipt' or something else?)
			- _from
			- timestamp
		"""
		pass

	def onPresenceReceived(self, _type, name, _from, last):
		u"""
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
		u"""
		Called when disconnected from whatsapp
		"""

	def onContactTyping(self, number):
		u"""
		Called when contact starts to type

		Args:
			- number: (str) cellphone number of contact
		"""
		pass

	def onContactPaused(self, number):
		u"""
		Called when contact stops typing

		Args:
			- number: (str) cellphone number of contact
		"""
		pass

	def	onTextMessage(self, _id, _from, to, notify, timestamp, participant, offline, retry, body):
		u"""
		Called when text message is received

		Args:
			- _id:
			- _from: (str) jid of of sender
			- to:
			- notify: (str) human readable name of _from (e.g. John Smith)
			- timestamp:
			- participant: (str) jid of user who sent the message in a groupchat
			- offline:
			- retry:
			- body: The content of the message
		"""
		pass

	def onImage(self, entity):
		u"""
		Called when image message is received

		Args:
			- entity: ImageDownloadableMediaMessageProtocolEntity
		"""
		pass

	def onAudio(self, entity):
		u"""
		Called when audio message is received

		Args:
			- entity: AudioDownloadableMediaMessageProtocolEntity
		"""
		pass


	def onVideo(self, entity):
		u"""
		Called when video message is received

		Args:
			- entity: VideoDownloadableMediaMessageProtocolEntity
		"""
		pass

	def onLocation(self, entity):
		u"""
		Called when location message is received

		Args:
			- entity: LocationMediaMessageProtocolEntity
		"""
		pass

	def onVCard(self, _id, _from, name, card_data, to, notify, timestamp, participant):
		u"""
		Called when VCard message is received

		Args:
			- _id: (str) id of entity
			- _from:
			- name:
			- card_data:
			- to:
			- notify:
			- timestamp:
			- participant:
		"""
		pass

	def onAddedToGroup(self, entity):
		u"""Called when the user has been added to a new group"""
		pass

	def onParticipantsAddedToGroup(self, entity):
		u"""Called when participants have been added to a group"""
		pass

	def onParticipantsRemovedFromGroup(self, group, participants):
		u"""Called when participants have been removed from a group
		
		Args:
			- group: (str) id of the group (e.g. 27831788123-144024456)
			- participants: (list) jids of participants that are removed
		"""
		pass

	def sendEntity(self, entity):
		u"""Sends an entity down the stack (as if YowsupAppLayer called toLower)"""
		self.stack.broadcastEvent(YowLayerEvent(YowsupAppLayer.TO_LOWER_EVENT,
			entity = entity
		))

	def sendIq(self, iq, onSuccess = None, onError = None):
		self.stack.broadcastEvent(
			YowLayerEvent(
				YowsupAppLayer.SEND_IQ,
				iq = iq,
				success = onSuccess,
				failure = onError,
			)
		)

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback

class YowsupAppLayer(YowInterfaceLayer):
	EVENT_START = u'transwhat.event.YowsupAppLayer.start'
	TO_LOWER_EVENT = u'transwhat.event.YowsupAppLayer.toLower'
	SEND_IQ = u'transwhat.event.YowsupAppLayer.sendIq'

	def onEvent(self, layerEvent):
		# We cannot pass instance varaibles in through init, so we use an event
		# instead
		# Return False if you want the event to propogate down the stack
		# return True otherwise
		if layerEvent.getName() == YowsupAppLayer.EVENT_START:
			self.caller = layerEvent.getArg(u'caller')
			self.logger = logging.getLogger(self.__class__.__name__)
			return True
		elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
			self.caller.onDisconnect()
			return True
		elif layerEvent.getName() == YowsupAppLayer.TO_LOWER_EVENT:
			self.toLower(layerEvent.getArg(u'entity'))
			return True
		elif layerEvent.getName() == YowsupAppLayer.SEND_IQ:
			iq = layerEvent.getArg(u'iq')
			success = layerEvent.getArg(u'success')
			failure = layerEvent.getArg(u'failure')
			self._sendIq(iq, success, failure)
			return True
		return False

	@ProtocolEntityCallback(u'success')
	def onAuthSuccess(self, entity):
		# entity is SuccessProtocolEntity
		status = entity.status
		kind = entity.kind
		creation = entity.creation
		expiration = entity.expiration
		props = entity.props
		nonce = entity.nonce
		t = entity.t # I donu't know what this is
		self.caller.onAuthSuccess(status, kind, creation, expiration, props, nonce, t)

	@ProtocolEntityCallback('failureu')
	def onAuthFailure(self, entity):
		# entity is FailureProtocolEntity
		reason = entity.reason
		self.caller.onAuthFailure(reason)

	@ProtocolEntityCallback('receiptu')
	def onReceipt(self, entity):
		"""Sends ack automatically"""
		# entity is IncomingReceiptProtocolEntity
		ack = OutgoingAckProtocolEntity(entity.getId(),
				'receiptu', entity.getType(), entity.getFrom())
		self.toLower(ack)
		_id = entity._id
		_from = entity._from
		timestamp = entity.timestamp
		type = entity.type
		participant = entity.participant
		offline = entity.offline
		items = entity.items
		self.caller.onReceipt(_id, _from, timestamp, type, participant, offline, items)

	@ProtocolEntityCallback('acku')
	def onAck(self, entity):
		# entity is IncomingAckProtocolEntity
		self.caller.onAck(
			entity._id,
			entity._class,
			entity._from,
			entity.timestamp
		)

	@ProtocolEntityCallback('notificationu')
	def onNotification(self, entity):
		"""
		Sends ack automatically
		"""
		self.logger.debug("Received notification (%s): %s", type(entity), entity)
		self.toLower(entity.ack())
		if isinstance(entity, CreateGroupsNotificationProtocolEntity):
			self.caller.onAddedToGroup(entity)
		elif isinstance(entity, AddGroupsNotificationProtocolEntity):
			self.caller.onParticipantsAddedToGroup(entity)
		elif isinstance(entity, RemoveGroupsNotificationProtocolEntity):
			self.caller.onParticipantsRemovedFromGroup(
					entity.getGroupId().split('@u')[0],
					entity.getParticipants().keys()
			)

	@ProtocolEntityCallback('messageu')
	def onMessageReceived(self, entity):
		self.logger.debug("Received Message: %s", entity)
		if entity.getType() == MessageProtocolEntity.MESSAGE_TYPE_TEXT:
			self.caller.onTextMessage(
				entity._id,
				entity._from,
				entity.to,
				entity.notify,
				entity.timestamp,
				entity.participant,
				entity.offline,
				entity.retry,
				entity.body
			)
		elif entity.getType() == MessageProtocolEntity.MESSAGE_TYPE_MEDIA:
			if isinstance(entity, ImageDownloadableMediaMessageProtocolEntity):
				# There is just way too many fields to pass them into the
				# function
				self.caller.onImage(entity)
			elif isinstance(entity, AudioDownloadableMediaMessageProtocolEntity):
				self.caller.onAudio(entity)
			elif isinstance(entity, VideoDownloadableMediaMessageProtocolEntity):
				self.caller.onVideo(entity)
			elif isinstance(entity, VCardMediaMessageProtocolEntity):
				self.caller.onVCard(
					entity._id,
					entity._from,
					entity.name,
					entity.card_data,
					entity.to,
					entity.notify,
					entity.timestamp,
					entity.participant
				)
			elif isinstance(entity, LocationMediaMessageProtocolEntity):
				self.caller.onLocation(entity)

	@ProtocolEntityCallback('presenceu')
	def onPresenceReceived(self, presence):
		_type = presence.getType()
		name = presence.getName()
		_from = presence.getFrom()
		last = presence.getLast()
		self.caller.onPresenceReceived(_type, name, _from, last)

	@ProtocolEntityCallback('chatstateu')
	def onChatstate(self, chatstate):
		number = chatstate._from.split('@')[0]
		if chatstate.getState() == ChatstateProtocolEntity.STATE_TYPING:
			self.caller.onContactTyping(number)
		else:
			self.caller.onContactPaused(number)
