import pytest
from spectrum2 import Backend
from transWhat.whatsappbackend import WhatsAppBackend
from unittest.mock import Mock, create_autospec, patch


@pytest.mark.asyncio
@patch("transWhat.whatsappbackend.Session")
async def test_handle_login_request(mock_session):
    jid = "magic@jid.com"

    user_name = "user@jid.com"
    password = "password"
    legacy_name = "0000"
    extra = []

    mock_io = create_autospec(Backend)
    backend = WhatsAppBackend(mock_io, user_name, {})

    await backend.handle_login_request(user_name, legacy_name, password, extra)

    mock_session(backend, user_name, legacy_name, extra).login.assert_called_with(
        password
    )

    assert user_name in backend.sessions
