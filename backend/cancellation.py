from contextlib import contextmanager
from threading import Event, RLock


class AnalysisCancelled(Exception):
    pass


class Cancellation:
    def __init__(self):
        self.event = Event()
        self.lock = RLock()
        self.stoppers = set()
        self.finished = False

    def check(self):
        if self.event.is_set():
            raise AnalysisCancelled()

    @contextmanager
    def watch(self, stop):
        with self.lock:
            self.check()
            self.stoppers.add(stop)
        try:
            yield
        finally:
            with self.lock:
                self.stoppers.discard(stop)

    def cancel(self):
        with self.lock:
            if self.finished:
                return False
            self.event.set()
            stops = list(self.stoppers)
        for stop in stops:
            try:
                stop()
            except OSError:
                pass
        return True

    def commit(self, save):
        with self.lock:
            self.check()
            result = save()
            self.finished = True
            return result
