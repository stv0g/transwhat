import pytest
from asyncio import Transport
from spectrum2 import Backend
from transWhat.session import Session
from unittest.mock import create_autospec
from yowsup.stacks import YowStack
from collections import deque
from transWhat.yowsupwrapper import YowsupAppLayer


class MockYowstack:
    def __init__(self):
        self.events = deque()
        self.props = {}

    def setProp(self, key, value):
        self.props[key] = value

    def broadcastEvent(self, event):
        self.events.append(event)

    def assert_event_called(self, event_name, **kwargs):
        for event in self.events:
            if event.name != event_name:
                continue

            if event.args != kwargs:
                continue

            return

        raise AssertionError(
            f"event name={event_name}, args={kwargs} not found in {self.events}"
        )

    def assert_entity_called(self, entity):
        _qualname = type(entity).__qualname__

        for event in self.events:
            if event.name != YowsupAppLayer.TO_LOWER_EVENT:
                continue

            got_entity = event.args["entity"]

            is_equal = all(
                (
                    _qualname == type(got_entity).__qualname__,
                    got_entity.__dict__ == entity.__dict__,
                )
            )

            if is_equal:
                return

        raise AssertionError(f"entity {entity} not found in {self.events}")

    def assert_iq_called(self, iq_type, success=None, failure=None):
        _qualname = iq_type.__qualname__

        for event in self.events:
            if event.name != YowsupAppLayer.SEND_IQ:
                continue

            iq = event.args["iq"]

            if type(iq).__qualname__ != _qualname:
                continue

            if event.args["success"] != success:
                continue

            if event.args["failure"] != failure:
                continue

            return

        raise AssertionError(
            f"iq type={iq_type} success={success} error={error} not found in {self.events}"
        )


@pytest.fixture
def mock_transport() -> Transport:
    yield create_autospec(Transport)


@pytest.fixture
def mock_session() -> Session:
    yield create_autospec(Session)


@pytest.fixture
def mock_backend() -> Backend:
    yield create_autospec(Backend)


@pytest.fixture
def mock_yowstack():
    return MockYowstack()
