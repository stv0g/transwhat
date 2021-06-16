from pytest import raises
from unittest.mock import Mock
from transWhat.deferred import Deferred, DeferredHasValue, call


def test_deferred_argument_forwarding_works():
    test_cases = [[], [1], [1, 2], [1, 2, 3]]

    for test_case in test_cases:
        cb = Mock()

        fut = Deferred()
        fut.then(cb)

        fut.run(*test_case)

        cb.assert_called_with(*test_case)


def test_deferred_pipelining_works():
    cb = Mock()

    fut = Deferred()
    fut.append(2)
    fut.then(cb)
    fut.run([1])

    cb.assert_called_with([1, 2])


def test_deferred_raises_when_running_twice():
    cb = Mock()

    fut = Deferred()
    fut.then(cb)
    fut.run()

    with raises(DeferredHasValue):
        fut.run()


def test_call_appends_arguments():
    cb = Mock()

    fut = Deferred()
    fut.extend((1, 2))
    fut.run([])

    call(cb, fut)

    cb.assert_called_with([1, 2])
