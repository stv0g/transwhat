import pytest
from spectrum2 import Backend
from transWhat.session import Session
from transWhat.whatsappbackend import WhatsAppBackend
from unittest.mock import Mock, create_autospec, patch


@pytest.fixture
def mock_session() -> Session:
    yield create_autospec(Session)


@pytest.fixture
def mock_io() -> Backend:
    yield create_autospec(Backend)


@patch("transWhat.whatsappbackend.Session")
def test_login_logout_work(mock_session_cls, mock_io, mock_session):
    jid = "magic@jid.com"

    user_name = "user@jid.com"
    password = "password"
    legacy_name = "0000"
    extra = []

    backend = WhatsAppBackend(mock_io, user_name, {})

    # Login
    backend.handle_login_request(user_name, legacy_name, password, extra)
    mock_session = mock_session_cls(backend, user_name, legacy_name, extra)
    assert user_name in backend.sessions
    mock_session.login.assert_called_with(password)

    # Logout
    backend.handle_logout_request(user_name, legacy_name)
    mock_session.logout.assert_called()


def test_handle_message_send_request(mock_io, mock_session):
    user_name = "user@jid.com"

    mock_user = "mock@jid.com"
    mock_sender = "sender@jid.com"
    mock_message = "my message"
    mock_id = "id"

    backend = WhatsAppBackend(mock_io, user_name, {})
    backend.sessions[user_name] = mock_session

    backend.handle_message_send_request(user_name, mock_sender, mock_message, mock_id)
    mock_session.sendMessageToWA.assert_called_with(
        mock_sender, mock_message, "", mock_id
    )


def test_handle_join_and_leave_room(mock_io, mock_session):
    user_name = "user@jid.com"
    room_name = "test room"
    nick_name = "test nick"
    password = "password"  # why?

    backend = WhatsAppBackend(mock_io, user_name, {})
    backend.sessions[user_name] = mock_session

    # Join room
    backend.handle_join_room_request(user_name, room_name, nick_name, password)
    mock_session.joinRoom.assert_called_with(room_name, nick_name)

    # Leave room
    backend.handle_leave_room_request(user_name, room_name)
    mock_session.leaveRoom.assert_called_with(room_name)
