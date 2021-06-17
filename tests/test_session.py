import pytest

from unittest.mock import patch, Mock, create_autospec
from transWhat.session import Session
from typing import Optional
from yowsup.structs import ProtocolEntity
from yowsup.stacks import YowStack
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_privacy.protocolentities.privacylist_iq import (
    PrivacyListIqProtocolEntity,
)
from yowsup.layers.protocol_iq.protocolentities.iq_push import PushIqProtocolEntity
from yowsup.layers.protocol_iq.protocolentities.iq_props import PropsIqProtocolEntity
from transWhat.yowsupwrapper import YowsupAppLayer
from contextlib import contextmanager
from yowsup.layers.protocol_presence.protocolentities import (
    AvailablePresenceProtocolEntity,
    UnavailablePresenceProtocolEntity,
)

from yowsup.layers.protocol_media.protocolentities import (
    MediaMessageProtocolEntity,
    DownloadableMediaMessageProtocolEntity,
    ImageDownloadableMediaMessageProtocolEntity,
)


@pytest.fixture
def session_instance(mock_backend, mock_yowstack):
    mock_user = "mock@user.com"
    mock_legacy_name = "legacy name"

    sess = Session(
        backend=mock_backend, user=mock_user, legacyName=mock_legacy_name, extra=[]
    )
    sess.stack = mock_yowstack

    yield sess


def test_login_works(session_instance, mock_yowstack):
    password = "test password"

    session_instance.login(password)
    assert session_instance.password == password
    mock_yowstack.assert_event_called(YowNetworkLayer.EVENT_STATE_CONNECT)


def test_logout_works(session_instance, mock_yowstack):
    session_instance.loggedIn = True

    session_instance.logout()
    assert not session_instance.loggedIn

    mock_yowstack.assert_event_called(YowNetworkLayer.EVENT_STATE_DISCONNECT)


def test_send_message_to_xmpp_queued(session_instance, mock_backend):
    session_instance.initialized = False

    session_instance.sendMessageToXMPP(
        buddy="test@jid.com",
        message="this is a random message",
        timestamp=1,
    )

    assert not mock_backend.handle_message.called


def test_send_message_to_xmpp_proper(session_instance, mock_backend):
    session_instance.initialized = True

    session_instance.sendMessageToXMPP(
        buddy="test@jid.com", message="this is a random message", timestamp=1
    )

    mock_backend.handle_message.assert_called_with(
        "mock@user.com",
        "test@jid.com",
        "this is a random message",
        "",  # why
        "",  # why
        "19700101T000001",
    )


@pytest.mark.skip("updateRoomList and _updateGroups are broken and do not work")
def test_update_room_list(session_instance):
    raise NotImplementedError()


@pytest.mark.skip("joinRoom depends on updateRoomList which does not work yet")
def test_join_room(session_instance):
    raise NotImplementedError()


@pytest.mark.skip("leaveRoom depends on updateRoomList which does not work yet")
def test_leave_room(session_instance):
    raise NotImplementedError()


def test_callback_on_auth_success(session_instance, mock_backend, mock_yowstack):
    session_instance.onAuthSuccess("success", 123, 1, 1, 1, 1, 1)

    assert session_instance.initialized
    assert session_instance.loggedIn

    # Interaction with backend works
    mock_backend.handle_connected.assert_called_with(session_instance.user)
    mock_backend.handle_buddy_changed.assert_called()

    # Interaction with Yowsup, these are called in subfunctions
    # TODO: check for toLower call
    mock_yowstack.assert_iq_called(PushIqProtocolEntity)
    mock_yowstack.assert_iq_called(PrivacyListIqProtocolEntity)
    mock_yowstack.assert_iq_called(PropsIqProtocolEntity)

    # .. and presence is true now
    mock_yowstack.assert_entity_called(AvailablePresenceProtocolEntity())


def test_callback_on_auth_failed(session_instance, mock_backend):
    session_instance.onAuthFailed("reason")

    mock_backend.handle_disconnected.assert_called()

    assert not session_instance.loggedIn
    assert session_instance.password is None


def test_callback_on_disconnect(session_instance, mock_backend):
    session_instance.onDisconnect()

    mock_backend.handle_disconnected.assert_called()


def test_callback_on_media_works_with_images(session_instance, mock_backend):
    media_inst = create_autospec(DownloadableMediaMessageProtocolEntity)

    media_inst.media_type = MediaMessageProtocolEntity.TYPE_MEDIA_IMAGE
    media_inst.url = "http://test.com/a-picture"
    media_inst.caption = "my first image"
    media_inst.participant = None
    media_inst.getFrom.return_value = "buddy"
    media_inst.getTimestamp.return_value = 1
    # media_inst.isEncrypted.return_value = False

    session_instance.onMedia(media_inst, "image")
