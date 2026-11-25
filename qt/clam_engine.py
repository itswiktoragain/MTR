import subprocess
from pathlib import Path
from engine_settings import BASE, BUNDLE
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

def update_db():
    db = BASE / "db"
    db.mkdir(parents=True, exist_ok=True)
    config = BASE / "freshclam.conf"
    config.write_text('DatabaseDirectory "' + str(db) + '"\nDatabaseMirror database.clamav.net\n', encoding="utf-8")
    log = BASE / "freshclam.log"
    with log.open("wb") as out:
        p = subprocess.run([str(BUNDLE / "freshclam.exe"), "--config-file=" + str(config)], cwd=BUNDLE, stdout=out, stderr=subprocess.STDOUT, timeout=1200, creationflags=FLAGS)
    if p.returncode or not signatures():
        raise RuntimeError("ClamAV signature update failed. See " + str(log))

def signatures():
    db = BASE / "db"
    return list(db.glob("*.cvd")) + list(db.glob("*.cld"))

def version():
    if not (BUNDLE / "clamscan.exe").is_file():
        raise RuntimeError("ClamAV not installed")
    return subprocess.check_output([str(BUNDLE / "clamscan.exe"), "--version"], cwd=BUNDLE, creationflags=FLAGS, timeout=15).decode(errors="replace").strip()
