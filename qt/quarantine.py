import hashlib, json, os, uuid
from engine_settings import BASE
from file_scan import regular, identity

def quarantine(path, expected, digest, name, roots, enabled):
    if not enabled or not any(path.is_relative_to(r) for r in roots):
        return "Not moved (scope or settings)."
    try:
        a = regular(path)
        if a is None or identity(a) != expected or a.st_nlink != 1:
            return "Not moved (identity changed or hard link)."
        q = BASE / "quarantine"
        q.mkdir(parents=True, exist_ok=True)
        if any(p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 1024 for p in (q, *q.parents)):
            return "Unsafe quarantine directory."
        if q.stat().st_dev != a.st_dev:
            return "Not moved (different drive)."
        with path.open("rb") as f:
            actual = hashlib.file_digest(f, "sha256").hexdigest()
        b = regular(path)
        if actual != digest or b is None or identity(b) != expected:
            return "Not moved (file changed)."
        dest = q / (uuid.uuid4().hex + ".mtr-quarantine")
        meta = dest.with_suffix(".json")
        meta.write_text(json.dumps({"original": str(path), "signature": name, "sha256": digest, "file": dest.name}, indent=2), encoding="utf-8")
        try:
            os.rename(path, dest)
        except OSError:
            meta.unlink(missing_ok=True)
            raise
        return "Moved to quarantine: " + str(dest)
    except OSError as e:
        return "Quarantine failed: " + str(e)
