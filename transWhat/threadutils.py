import queue
import threading

# This queue is for other threads that want to execute code in the main thread
eventQueue = queue.Queue()

def runInThread(threadFunc, callback):
    """
    Executes threadFunc in a new thread. The result of threadFunc will be
    pass as the first argument to callback. callback will be called in the main
    thread.
    """
    def helper():
        # Execute threadfunc in new thread
        result = threadFunc()
        # Queue callback to be call in main thread
        eventQueue.put(lambda: callback(result))

    thread = threading.Thread(target=helper)
    thread.start()
