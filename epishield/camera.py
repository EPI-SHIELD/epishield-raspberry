import threading
import time
from datetime import datetime, timezone


class Camera:
    """One reader, one most recent frame; no disk writes and no frame queue."""
    def __init__(self, device):
        import cv2
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.condition = threading.Condition()
        self.stopped = threading.Event()
        self.sequence, self.latest, self.error = 0, None, None
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        while not self.stopped.is_set():
            ok, frame = self.cap.read()
            with self.condition:
                if ok:
                    self.sequence += 1
                    self.latest = (self.sequence, datetime.now(timezone.utc), time.monotonic(), frame)
                    self.error = None
                else:
                    self.error = "Webcam indisponível"
                self.condition.notify_all()
            if not ok:
                self.stopped.wait(0.2)

    def fresh(self, after, timeout=3):
        end = time.monotonic() + timeout
        with self.condition:
            while time.monotonic() < end:
                if self.latest and self.latest[2] > after and not self.error:
                    seq, utc, mono, frame = self.latest
                    return seq, utc, mono, frame.copy()
                self.condition.wait(min(0.1, max(0, end-time.monotonic())))
        raise RuntimeError("Webcam sem captura nova")

    def close(self):
        self.stopped.set()
        self.cap.release()
        self.thread.join(timeout=2)
