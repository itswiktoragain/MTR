import os, queue, threading
from pathlib import Path
from collections import OrderedDict
import psutil
from engine_settings import BASE, BUNDLE
from file_scan import scan, regular, identity
from quarantine import quarantine

class Worker:
    def __init__(self,backend):
        self.b=backend;self.q=queue.Queue(4096);self.cache=OrderedDict();self.lock=threading.Lock();self.overflow=False;self.process_live=False
    def offer(self,raw):
        p=Path(raw).absolute()
        if p.is_relative_to(BASE) or p.is_relative_to(BUNDLE):return
        try:self.q.put_nowait(p)
        except queue.Full:self.overflow=True
    def run(self):
        while not self.b.stop_event.is_set():
            if not self.b.loaded or not self.b.daemon.proc or self.b.daemon.proc.poll() is not None:
                self.b.stop_event.wait(.5);continue
            try:p=self.q.get(timeout=.5)
            except queue.Empty:continue
            try:
                self.b.stop_event.wait(.1)
                if not self.b.stop_event.is_set():self.inspect(p,True)
            except Exception:self.b.errors+=1
            finally:self.q.task_done()
    def processes(self):
        user=psutil.Process().username().casefold();seen=set()
        while not self.b.stop_event.is_set():
            current=set()
            try:
                for p in psutil.process_iter(["pid","create_time","exe","username"]):
                    i=p.info
                    if i["exe"] and i["username"] and i["username"].casefold()==user:
                        k=(i["pid"],i["create_time"]);current.add(k)
                        if k not in seen:self.offer(i["exe"])
                seen=current;self.process_live=True
            except Exception:self.process_live=False
            self.b.stop_event.wait(1)
    def start(self):
        for f in (self.run,self.processes):threading.Thread(target=f,daemon=True).start()

    def inspect(self,path,automatic=False):
        path=Path(path).absolute()
        if path.is_relative_to(BASE) or path.is_relative_to(BUNDLE):return "skipped"
        s=regular(path)
        if s is None:return "skipped"
        key=(path,identity(s))
        with self.lock:
            if automatic and key in self.cache:return "cached"
        verdict,detail,expected,digest=scan(self.b.daemon,path)
        if verdict=="retry":
            self.b.stop_event.wait(.2)
            verdict,detail,expected,digest=scan(self.b.daemon,path)
        if verdict in ("clean","found"):
            with self.lock:
                self.cache[key]=True
                if len(self.cache)>16000:self.cache.popitem(last=False)
        if verdict=="found":
            action=quarantine(path,expected,digest,detail,self.b.folders,self.b.auto_quarantine)
            self.b.event("Malware signature detected","Signature: "+detail+"\nFile: "+str(path)+"\nSHA-256: "+digest+"\nAction: "+action+"\nA running process may already have executed.","warning","SIGNATURE")
        elif verdict=="skipped":self.b.skips+=1
        elif verdict in ("error","retry"):self.b.errors+=1
        return verdict
