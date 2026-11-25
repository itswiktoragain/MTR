import os, socket, subprocess, time
from engine_settings import BASE, BUNDLE
from clam_engine import FLAGS, signatures
class Daemon:
    def __init__(self,base=BASE,bundle=BUNDLE):
        self.base=base;self.bundle=bundle;self.stopped=False
        self.base.mkdir(parents=True,exist_ok=True)
        self.proc=None
        self.port=None
        self.log=None
    def start(self,test=False):
        if self.stopped:raise RuntimeError("Engine stopped")
        self.close()
        if not test and not signatures():raise RuntimeError("Signature database missing")
        with socket.socket() as s:
            s.bind(("127.0.0.1",0));self.port=s.getsockname()[1]
        cfg=self.base/"clamd.conf"
        cfg.write_text('DatabaseDirectory "'+str(self.base/"db")+'"\nTCPAddr 127.0.0.1\nTCPSocket '+str(self.port)+'\nForeground yes\nMaxThreads 4\nStreamMaxLength 64M\nMaxFileSize 64M\nMaxScanSize 128M\nAlertExceedsMax yes\n',encoding="utf-8")
        self.log=(self.base/"clamd.log").open("wb")
        self.proc=subprocess.Popen([str(self.bundle/"clamd.exe"),"--config-file="+str(cfg)],cwd=self.bundle,stdout=self.log,stderr=subprocess.STDOUT,creationflags=FLAGS)
        for i in range(360):
            if self.stopped or not self.proc or self.proc.poll() is not None:break
            if self.ready():return
            time.sleep(.5)
        self.close();raise RuntimeError("ClamAV daemon did not start. See clamd.log.")
    def ready(self):
        try:
            return bool(self.proc and self.proc.poll() is None and self.command(b"PING")=="PONG")
        except (OSError,TypeError):return False
    def connect(self,timeout=60):
        return socket.create_connection(("127.0.0.1",self.port),timeout=timeout)
    @staticmethod
    def read(s):
        data=bytearray()
        while len(data)<8192:
            chunk=s.recv(1024)
            if not chunk:break
            data.extend(chunk)
            if b"\0" in chunk:break
        return bytes(data).split(b"\0",1)[0].decode("utf-8","replace").strip()
    def command(self,cmd):
        with self.connect(2) as s:
            s.sendall(b"z"+cmd+b"\0");return self.read(s)
    def close(self):
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
            self.proc=None
        if self.log:self.log.close();self.log=None
