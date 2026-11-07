"""سجل المراجعة البشرية: لا يصير مثال «معتمداً» إلا بتوقيع مراجع مسمّى.
الكود لا يستطيع التحقق أن الموقِّع إنسان؛ المسؤولية على من يستخدم الواجهة (CLI: studio review)."""
import json
import os
import tempfile
import time
import unicodedata
from pathlib import Path

VERDICTS = ("approved", "rejected", "needs_change")


def _key(kind, text):
    return f"{kind}:{unicodedata.normalize('NFC', text)}"


class ReviewLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {"entries": {}}

    def record(self, kind, text, verdict, reviewer, note=""):
        if verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if not reviewer or not reviewer.strip():
            raise ValueError("reviewer name is required")
        self.data["entries"][_key(kind, text)] = {"verdict": verdict, "reviewer": reviewer.strip(), "note": note,
                                                  "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        self._save()

    def status(self, kind, text):
        e = self.data["entries"].get(_key(kind, text))
        return e["verdict"] if e else "unreviewed"

    def entry(self, kind, text):
        return self.data["entries"].get(_key(kind, text))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
