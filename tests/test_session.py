import pytest

from transWhat.session import Session
from typing import Optional
from yowsup.stacks import YowStack
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer


@pytest.fixture
def session_instance(mock_backend, mock_yowstack):
    mock_user = "mock@user.com"
    mock_legacy_name = "legacy name"

    sess = Session(
        backend=mock_backend, user=mock_user, legacyName=mock_legacy_name, extra=[]
    )
    sess.stack = mock_yowstack

    yield sess


def assert_event_called(sess: Session, event_name):

    # This essentially gets the first argument of a broadcastEvent call
    # This is dirty, but we can do nothing about it for now
    events = [
        call[0][0] if call[0] else call[1].get("name")
        for call in sess.stack.broadcastEvent.call_args_list
    ]

    assert event_name in [event.name for event in events]


def get_events(sess: Session):
    sess.stack.broadcastEvent.call


def test_login_works(session_instance):
    password = "test password"

    session_instance.login(password)
    assert session_instance.password == password
    assert_event_called(session_instance, YowNetworkLayer.EVENT_STATE_CONNECT)


def test_logout_works(session_instance):
    session_instance.loggedIn = True

    session_instance.logout()
    assert not session_instance.loggedIn
    assert_event_called(session_instance, YowNetworkLayer.EVENT_STATE_DISCONNECT)
