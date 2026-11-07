"""سجل البحث: الادعاءات ومصادرها وحالتها. لا يخترع مصادر: المصدر يجب أن يملك عنواناً وإما رابطاً وإما اقتباساً مرجعياً كاملاً
يقدّمه الإنسان/المضيف. الادعاء من نوع fact بلا مصدر يُوسَم تلقائياً للمراجعة. ولا يغني البحث عن مراجعة المختص (خصوصاً الإملاء والنطق)."""
import json
import time
from pathlib import Path

KINDS = ("fact", "interpretation", "reconstruction", "uncertain")
STATUS = ("unverified", "verified", "disputed")
SPECIALIST_TOPICS = ("orthography", "pronunciation", "grammar", "religious_text", "medical", "scientific_claim")


class ResearchError(ValueError):
    pass


class ResearchLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.d = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {"claims": [], "sources": {}}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.path)

    def add_source(self, sid, title, url=None, citation=None, accessed=None, reliability_note=""):
        if not title or not title.strip():
            raise ResearchError("source title required")
        if not url and not citation:
            raise ResearchError("a source needs a url or a full citation (never invent one)")
        if url and not str(url).startswith(("http://", "https://")):
            raise ResearchError("url must be http(s)")
        self.d["sources"][sid] = {"title": title, "url": url, "citation": citation,
                                  "accessed": accessed or time.strftime("%Y-%m-%d"), "reliability_note": reliability_note}
        self._save()

    def add_claim(self, text, kind="fact", sources=(), topic=None, status="unverified", note=""):
        if kind not in KINDS:
            raise ResearchError(f"kind must be one of {KINDS}")
        if status not in STATUS:
            raise ResearchError(f"status must be one of {STATUS}")
        unknown = [s for s in sources if s not in self.d["sources"]]
        if unknown:
            raise ResearchError(f"unknown source ids: {unknown}")
        if status == "verified" and kind == "fact" and not sources:
            raise ResearchError("a verified fact needs at least one source")
        cid = f"c{len(self.d['claims']) + 1:03d}"
        specialist = topic in SPECIALIST_TOPICS
        self.d["claims"].append({"id": cid, "text": text, "kind": kind, "sources": list(sources), "topic": topic, "status": status,
                                 "needs_human_review": specialist or kind in ("uncertain", "reconstruction") or (kind == "fact" and not sources),
                                 "specialist_required": specialist, "note": note})
        self._save()
        return cid

    def mark_reviewed(self, cid, reviewer, status="verified"):
        if not reviewer.strip():
            raise ResearchError("reviewer required")
        c = next((x for x in self.d["claims"] if x["id"] == cid), None)
        if c is None:
            raise ResearchError(f"unknown claim {cid}")
        if status == "verified" and c["kind"] == "fact" and not c["sources"]:
            raise ResearchError("cannot verify an unsourced fact")
        c.update(status=status, needs_human_review=False, reviewed_by=reviewer.strip())
        self._save()

    def validate(self):
        issues = []
        for c in self.d["claims"]:
            if c["kind"] == "fact" and not c["sources"]:
                issues.append(f"{c['id']}: unsourced fact")
            if c["kind"] == "reconstruction" and "reconstruction" not in c["text"] and not c["note"]:
                issues.append(f"{c['id']}: reconstruction must be labelled as such")
        return issues

    def pending_review(self):
        return [c for c in self.d["claims"] if c["needs_human_review"]]

    def summary(self):
        cl = self.d["claims"]
        return {"claims": len(cl), "sources": len(self.d["sources"]), "verified": sum(c["status"] == "verified" for c in cl),
                "uncertain": sum(c["kind"] == "uncertain" for c in cl), "pending_human_review": len(self.pending_review()),
                "facts": sum(c["kind"] == "fact" for c in cl), "interpretations": sum(c["kind"] == "interpretation" for c in cl),
                "issues": self.validate()}

    def to_artifact(self):
        return {**self.d, "summary": self.summary()}

    def add_lesson_review_items(self, lesson):
        """يضيف عناصر مراجعة درس الحروف كادعاءات مختص مطلوب (بلا مصادر مختلقة)."""
        for r in lesson["review"]["needs_human_review"]:
            if r["status"] != "approved":
                self.add_claim(f"[{r['kind']}] {r['text']} — {r['reason']}", kind="uncertain", topic="orthography", note="from learning lesson")
