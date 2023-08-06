import threading

class StoppableThread(threading.Thread):
    # Copied from https://stackoverflow.com/questions/24843193/stopping-a-python-thread-running-an-infinite-loop
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.is_set()
