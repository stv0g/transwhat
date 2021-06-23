from unittest.mock import Mock
from transWhat.threadutils import eventQueue, runInThread


def test_runInThread():
    magic = object()

    def thread_func():
        return magic

    def callback(result):
        return result == magic

    runInThread(thread_func, callback)
    result = eventQueue.get(timeout=1.0)
    assert result
