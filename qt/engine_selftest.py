"""Safe integration test against an isolated custom signature database."""
import hashlib,tempfile
from pathlib import Path
from clam_daemon import Daemon
from file_scan import scan
def selftest():
    with tempfile.TemporaryDirectory(prefix="mtr-engine-test-") as tmp:
        base=Path(tmp); db=base/"db";db.mkdir()
        marker=b"MTR harmless engine integration marker 2026"
        (db/"test.hdb").write_text(hashlib.md5(marker).hexdigest()+":"+str(len(marker))+":MTR.Test.Marker\n",encoding="ascii")
        bad=base/"marker.bin";bad.write_bytes(marker)
        good=base/"clean.bin";good.write_bytes(b"ordinary integration test data")
        engine=Daemon(base=base)
        try:
            engine.start(test=True)
            result=scan(engine,bad);assert result[0]=="found" and "MTR.Test.Marker" in result[1],result
            result=scan(engine,good);assert result[0]=="clean",result
        finally:engine.close()
