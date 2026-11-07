"""حالة المشروع: ملف project.json + مراجعات مخرجات غير قابلة للتعديل artifacts/<stage>/r<N>.json.
الكتابة ذرّية (tmp + replace) ومحمية بقفل ملف لتفادي التعارض بين عمليتين."""
import json
import os
import tempfile
import time
import unicodedata
import uuid

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False
    try:
        import msvcrt
        _HAS_MSVCRT = True
    except ImportError:
        _HAS_MSVCRT = False
from contextlib import contextmanager
from pathlib import Path

from . import workflow as W


class StateError(Exception):
    pass


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Project:
    def __init__(self, root):
        self.root = Path(root)
        self.file = self.root / "project.json"
        if not self.file.exists():
            raise StateError(f"no project at {self.root} (run: studio new)")
        self.data = json.loads(self.file.read_text("utf-8"))

    # ---------- إنشاء/قفل/حفظ
    @classmethod
    def create(cls, root, name):
        root = Path(root)
        if (root / "project.json").exists():
            raise StateError(f"project already exists at {root}")
        for sub in ("artifacts", "tasks/pending", "tasks/done", "assets", "exports"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        data = {"project_id": "prj_" + uuid.uuid4().hex[:10], "name": unicodedata.normalize("NFC", name),
                "created": now(), "stages": {s: {"status": "pending", "revision": 0, "updated": None} for s in W.ORDER}}
        atomic_write(root / "project.json", json.dumps(data, ensure_ascii=False, indent=2))
        return cls(root)

    @property
    def id(self):
        return self.data["project_id"]

    @contextmanager
    def lock(self):
        (self.root / ".lock").touch()
        with open(self.root / ".lock", "w") as lf:
            if _HAS_FCNTL:
                fcntl.flock(lf, fcntl.LOCK_EX)
            elif _HAS_MSVCRT:
                msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
            self.data = json.loads(self.file.read_text("utf-8"))   # أعد القراءة بعد الحصول على القفل
            yield
            if _HAS_FCNTL:
                fcntl.flock(lf, fcntl.LOCK_UN)
            elif _HAS_MSVCRT:
                try:
                    msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass

    def save(self):
        atomic_write(self.file, json.dumps(self.data, ensure_ascii=False, indent=2))

    # ---------- استعلام
    def stage(self, sid):
        W.index(sid)
        return self.data["stages"][sid]

    def status(self, sid):
        return self.stage(sid)["status"]

    def revision_path(self, sid, rev):
        return self.root / "artifacts" / sid / f"r{rev:03d}.json"

    def artifact(self, sid, rev=None):
        rev = rev or self.stage(sid)["revision"]
        if not rev:
            return None
        p = self.revision_path(sid, rev)
        if not p.exists():
            raise StateError(f"missing artifact file {p}")
        return json.loads(p.read_text("utf-8"))

    def revisions(self, sid):
        return sorted(int(p.stem[1:]) for p in (self.root / "artifacts" / sid).glob("r*.json"))

    def next_stage(self):
        """أول مرحلة غير مجتازة، أو None إن اكتمل كل شيء."""
        for sid in W.ORDER:
            if self.status(sid) not in W.PASSING:
                return sid
        return None

    # ---------- كتابة
    def submit(self, sid, artifact, author="agent", note=""):
        """يسجّل مراجعة جديدة للمرحلة. يشترط اجتياز كل المراحل السابقة. لا يعدّل مراجعة قديمة أبداً."""
        with self.lock():
            st = W.BY_ID[sid]
            blocked = [u for u in W.upstream(sid) if self.status(u) not in W.PASSING]
            if blocked:
                raise StateError(f"cannot submit '{sid}': upstream not passed: {blocked}")
            if st.schema:
                from .schema import validate_file
                errs = validate_file(artifact, st.schema)
                if errs:
                    raise StateError(f"artifact for '{sid}' violates {st.schema}: " + "; ".join(errs[:5]))
            s = self.stage(sid)
            if s["status"] in ("approved", "done"):
                raise StateError(f"stage '{sid}' is '{s['status']}': use modify/rewind first (an approved revision is never overwritten)")
            rev = s["revision"] + 1
            atomic_write(self.revision_path(sid, rev), json.dumps(artifact, ensure_ascii=False, indent=2))
            s.update(revision=rev, status="awaiting_approval" if st.approval else "done", updated=now(),
                     author=author, note=note)
            self.save()
            return rev

    def set_status(self, sid, status, **extra):
        if status not in W.STATUSES:
            raise StateError(f"bad status {status}")
        with self.lock():
            s = self.stage(sid)
            s["status"] = status
            s["updated"] = now()
            s.update(extra)
            self.save()

    def invalidate_downstream(self, sid):
        """بعد التراجع/التعديل: كل ما بعد المرحلة يصير invalidated (مراجعاته القديمة تبقى للمقارنة)."""
        with self.lock():
            out = []
            for d in W.downstream(sid):
                s = self.stage(d)
                if s["status"] != "pending":
                    s["status"] = "invalidated"
                    s["updated"] = now()
                    out.append(d)
            self.save()
            return out
