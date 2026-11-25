import hashlib, os, stat, struct
from engine_settings import MAX_FILE
def regular(p):
    try:
        for x in (p,*p.parents):
            s=x.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,"st_file_attributes",0)&1024:return None
        s=p.stat()
        return s if stat.S_ISREG(s.st_mode) else None
    except OSError:return None
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def scan(daemon,path):
    a=regular(path)
    if a is None or a.st_size>MAX_FILE:return "skipped","Unsafe path or size limit",None,None
    digest=hashlib.sha256()
    try:
        with path.open("rb") as f:
            if identity(os.fstat(f.fileno()))!=identity(a):return "retry","File changed",None,None
            with daemon.connect() as s:
                s.sendall(b"zINSTREAM\0");size=0
                while chunk:=f.read(65536):
                    size+=len(chunk)
                    if size>MAX_FILE:return "skipped","Size limit",None,None
                    digest.update(chunk);s.sendall(struct.pack(">I",len(chunk))+chunk)
                s.sendall(b"\0"*4);answer=daemon.read(s)
            b=os.fstat(f.fileno())
        c=regular(path)
        if c is None or identity(a)!=identity(b) or identity(a)!=identity(c):return "retry","File changed",None,None
        if answer=="stream: OK":return "clean","No signature detected",identity(a),digest.hexdigest()
        if answer.startswith("stream: ") and answer.endswith(" FOUND"):
            name=answer[8:-6]
            if name.startswith("Heuristics.Limits.Exceeded"):return "skipped",name,None,None
            return "found",name,identity(a),digest.hexdigest()
        return "error",answer or "No response",None,None
    except OSError as e:return "error",str(e),None,None
