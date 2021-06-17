import pytest
from spectrum2 import Backend
from transWhat.session import Session
from unittest.mock import create_autospec
from yowsup.stacks import YowStack


@pytest.fixture
def mock_session() -> Session:
    yield create_autospec(Session)


@pytest.fixture
def mock_backend() -> Backend:
    yield create_autospec(Backend)


@pytest.fixture
def mock_yowstack() -> YowStack:
    yield create_autospec(YowStack)
