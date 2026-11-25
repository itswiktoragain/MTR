"""Independent user-mode ClamAV backend."""
import os, threading, time
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from clam_engine import update_db, signatures
from clam_daemon import Daemon
from live_monitor import Monitor, roots
from scan_worker import Worker
from engine_settings import BASE, BUNDLE

class Backend(QObject):
    completed=Signal(str,object,str)
    detection=Signal(object)
    monitor_status=Signal(bool,str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.stop_event=threading.Event();self.running=set()
        self.daemon=Daemon();self.folders=roots();self.worker=Worker(self)
        self.monitor=Monitor(self.worker.offer);self.auto_quarantine=False
        self.skips=0;self.errors=0;self.quick=None;self.full=None
        self.started=False;self.loaded=False;self.last_error=""
        self.setup_lock=threading.Lock();self.next_update=float("inf")
    def event(self,title,detail,level="info",event_id="MTR"):
        self.detection.emit({"time":datetime.now().astimezone().isoformat(),"title":title,"detail":detail,"level":level,"id":event_id})
    def run(self,key,job):
        if key in self.running:return False
        self.running.add(key)
        def execute():
            try:result=job();error=""
            except Exception as exc:result=None;error=str(exc)
            if not self.stop_event.is_set():self.completed.emit(key,result,error)
        threading.Thread(target=execute,daemon=True).start();return True
    def watch(self):
        if self.started:return
        self.started=True
        try:self.monitor.start(self.folders)
        except Exception as e:self.last_error=str(e)
        self.worker.start()
        def boot():
            try:
                with self.setup_lock:
                    if not signatures():update_db()
                    if not self.stop_event.is_set():self.daemon.start();self.loaded=True
            except Exception as e:
                self.last_error=str(e);self.event("Engine unavailable",self.last_error,"warning","ENGINE")
            self.next_update=time.monotonic()+3600
            if not self.stop_event.is_set():self.report()
        threading.Thread(target=boot,daemon=True).start()
    def report(self):
        ready=self.loaded and self.daemon.ready()
        live=self.monitor.observer.is_alive() and bool(self.folders) and not self.worker.overflow
        detail="Watching "+str(len(self.folders))+" user folders and new current-user process images. Skips: "+str(self.skips)+"; errors: "+str(self.errors)+"."
        if self.worker.overflow:detail+=" Queue overflow; run a manual scan."
        if not ready:detail="Engine unavailable or loading signatures. "+self.last_error
        self.monitor_status.emit(ready and live and self.worker.process_live,detail)
        return ready,live
    def health(self):
        def job():
            ready,live=self.report();db=signatures()
            newest=max((p.stat().st_mtime for p in db),default=0)
            return {"antivirus":ready,"realtime":ready and live,"behavior":ready and self.worker.process_live,"ioav":bool(db),"signature":self.daemon.command(b"VERSION") if ready else "not loaded","updated":datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M") if newest else "not downloaded","quick":self.quick,"full":self.full}
        self.run("health",job)
        if self.started and time.monotonic()>=self.next_update:
            self.next_update=time.monotonic()+14400;self.update()
    def update(self):
        def job():
            with self.setup_lock:
                update_db()
                if self.stop_event.is_set():return "Stopped."
                self.loaded=False;self.daemon.start();self.loaded=True
                with self.worker.lock:self.worker.cache.clear()
                self.last_error=""
            return "ClamAV signature database updated."
        return self.run("update",job)
    def scan(self,full=False):
        def job():
            if not self.loaded or not self.daemon.ready():raise RuntimeError("ClamAV is not ready. Download signatures first.")
            counts={}
            for root in ([Path.home()] if full else self.folders):
                for parent,dirs,files in os.walk(root,followlinks=False):
                    if self.stop_event.is_set():raise RuntimeError("Scan cancelled")
                    dirs[:]=[d for d in dirs if not (Path(parent)/d).is_relative_to(BASE) and not os.path.isjunction(Path(parent)/d) and not (Path(parent)/d).is_symlink()]
                    for name in files:
                        if self.stop_event.is_set():raise RuntimeError("Scan cancelled")
                        result=self.worker.inspect(Path(parent)/name);counts[result]=counts.get(result,0)+1
            when=datetime.now().strftime("%Y-%m-%d %H:%M")
            if full:self.full=when
            else:self.quick=when
            return "Scan complete. "+(", ".join(k+": "+str(v) for k,v in sorted(counts.items())) or "No readable files found.")
        return self.run("scan",job)
    def set_quarantine(self,value):
        self.auto_quarantine=bool(value)
        with self.worker.lock:self.worker.cache.clear()
    def close(self):
        if self.stop_event.is_set():return
        self.stop_event.set();self.monitor.close()
        self.loaded=False;self.daemon.stopped=True;self.daemon.close()
