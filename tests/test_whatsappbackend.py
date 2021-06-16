import pytest
from spectrum2 import Backend
from transWhat.whatsappbackend import WhatsAppBackend
from unittest.mock import Mock, create_autospec, patch


@patch("transWhat.whatsappbackend.Session")
def test_login_logout_work(mock_session_cls):
    jid = "magic@jid.com"

    user_name = "user@jid.com"
    password = "password"
    legacy_name = "0000"
    extra = []

    mock_io = create_autospec(Backend)
    backend = WhatsAppBackend(mock_io, user_name, {})

    backend.handle_login_request(user_name, legacy_name, password, extra)

    mock_session = mock_session_cls(backend, user_name, legacy_name, extra)

    assert user_name in backend.sessions
    mock_session.login.assert_called_with(password)

    backend.handle_logout_request(user_name, legacy_name)
    mock_session.logout.assert_called()
