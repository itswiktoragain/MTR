from pathlib import Path
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def roots():
    h = Path.home()
    a = Path(os.environ.get("APPDATA", str(h)))
    paths = [h/"Downloads", h/"Desktop", h/"Documents", Path(os.environ.get("TEMP", str(h/"Temp"))), a/"Microsoft/Windows/Start Menu/Programs/Startup"]
    return [p.absolute() for p in paths if p.is_dir()]

class Monitor(FileSystemEventHandler):
    def __init__(self, offer):
        self.offer = offer
        self.observer = Observer()
    def on_any_event(self, e):
        if not e.is_directory and e.event_type in ("created", "modified", "moved"):
            self.offer(getattr(e, "dest_path", "") or e.src_path)
    def start(self, paths):
        for path in paths:
            self.observer.schedule(self, str(path), recursive=True)
        self.observer.start()
    def close(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=2)
