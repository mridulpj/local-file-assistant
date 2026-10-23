"""Terminal UI helpers."""
import itertools
import threading
import time


class Spinner:
    def __init__(self, label="Thinking"):
        self.label = label
        self._width = 0
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        for dots in itertools.cycle(["   ", ".  ", ".. ", "..."]):
            if self._done.is_set():
                break
            text = f"{self.label}{dots}"
            self._width = max(self._width, len(text))
            print("\r" + text.ljust(self._width), end="", flush=True)
            time.sleep(0.2)

    def start(self):
        self._thread.start()

    def stop(self):
        if not self._done.is_set():
            self._done.set()
            self._thread.join()
            print("\r" + " " * self._width + "\r", end="", flush=True)
