"""سجل الاعتماد (إلحاق فقط) + إجراءات: approve / reject / modify / regenerate_section / rewind / compare / resume.
كل سجل: project_id, stage_id, decision, timestamp, revision, feedback, actor (+ سلسلة بصمات).
السلسلة تكشف العبث العرضي والتعديل اللاحق (tamper-evident) لكنها لا تمنع من يملك الملف من إعادة كتابتها كلها
(tamper-proof يتطلب توقيعاً خارجياً). الكود لا يستطيع إثبات أن actor إنسان؛ المسؤولية على واجهة الاستعمال."""
import hashlib
import json
from pathlib import Path

from . import workflow as W
from .state import Project, StateError, atomic_write, canonical, now

DECISIONS = ("approve", "reject", "modify", "regenerate_section", "rewind")


class ApprovalError(StateError):
    pass


def _path_parts(path):
    import re
    return [int(t) if t.isdigit() else t for t in re.findall(r"[^.\[\]]+", path)]


def get_path(doc, path):
    for p in _path_parts(path):
        doc = doc[p]
    return doc


def set_path(doc, path, value):
    parts = _path_parts(path)
    cur = doc
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def diff(a, b, path="$"):
    """فروق بنيوية بين مستندين JSON: قائمة {path, a, b}."""
    if type(a) is not type(b):
        return [{"path": path, "a": a, "b": b}]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append({"path": f"{path}.{k}", "a": None, "b": b[k], "change": "added"})
            elif k not in b:
                out.append({"path": f"{path}.{k}", "a": a[k], "b": None, "change": "removed"})
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        out = []
        for i in range(max(len(a), len(b))):
            if i >= len(a):
                out.append({"path": f"{path}[{i}]", "a": None, "b": b[i], "change": "added"})
            elif i >= len(b):
                out.append({"path": f"{path}[{i}]", "a": a[i], "b": None, "change": "removed"})
            else:
                out += diff(a[i], b[i], f"{path}[{i}]")
        return out
    return [] if a == b else [{"path": path, "a": a, "b": b}]


class Approvals:
    def __init__(self, project: Project):
        self.p = project
        self.file = project.root / "approvals.jsonl"

    # ---------- السجل
    def records(self):
        if not self.file.exists():
            return []
        return [json.loads(l) for l in self.file.read_text("utf-8").splitlines() if l.strip()]

    def _append(self, stage, decision, revision, feedback="", actor="", section=None):
        if not actor or not actor.strip():
            raise ApprovalError("actor (reviewer name) is required")
        recs = self.records()
        prev = recs[-1]["hash"] if recs else "0" * 64
        rec = {"seq": len(recs) + 1, "project_id": self.p.id, "stage_id": stage, "decision": decision,
               "timestamp": now(), "revision": revision, "feedback": feedback, "actor": actor.strip(), "section": section,
               "prev_hash": prev}
        rec["hash"] = hashlib.sha256((prev + canonical(rec)).encode("utf-8")).hexdigest()
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def verify(self):
        """يعيد قائمة مشاكل السلسلة (فارغة = سليمة)."""
        prev, issues = "0" * 64, []
        for r in self.records():
            body = {k: v for k, v in r.items() if k != "hash"}
            if r["prev_hash"] != prev:
                issues.append(f"seq {r['seq']}: broken chain")
            if hashlib.sha256((r["prev_hash"] + canonical(body)).encode("utf-8")).hexdigest() != r["hash"]:
                issues.append(f"seq {r['seq']}: record altered")
            prev = r["hash"]
        return issues

    def history(self, stage=None):
        return [r for r in self.records() if stage in (None, r["stage_id"])]

    # ---------- الإجراءات
    def _need(self, stage, *statuses):
        st = self.p.status(stage)
        if st not in statuses:
            raise ApprovalError(f"stage '{stage}' is '{st}', expected one of {statuses}")

    def approve(self, stage, actor, revision=None, feedback=""):
        self._need(stage, "awaiting_approval")
        latest = self.p.stage(stage)["revision"]
        if revision is not None and revision != latest:
            raise ApprovalError(f"stale approval: you reviewed r{revision} but latest is r{latest}")
        rec = self._append(stage, "approve", latest, feedback, actor)
        self.p.set_status(stage, "approved", approved_revision=latest, approved_by=actor)
        return rec

    def reject(self, stage, actor, feedback):
        if not feedback or not feedback.strip():
            raise ApprovalError("feedback is required when rejecting")
        self._need(stage, "awaiting_approval")
        rec = self._append(stage, "reject", self.p.stage(stage)["revision"], feedback, actor)
        self.p.set_status(stage, "rejected", feedback=feedback)
        return rec

    def modify(self, stage, actor, feedback, new_artifact=None):
        """new_artifact مُعطى: تعديل بشري مباشر → مراجعة جديدة بانتظار اعتماد. غير مُعطى: يطلب من الوكيل التعديل."""
        if not feedback or not feedback.strip():
            raise ApprovalError("feedback is required")
        self._need(stage, "awaiting_approval", "approved", "rejected", "needs_modification")
        was_approved = self.p.status(stage) == "approved"
        if new_artifact is not None:
            rev = self.p.submit(stage, new_artifact, author=actor, note="human modification") if not was_approved \
                else self._resubmit_approved(stage, new_artifact, actor)
        else:
            rev = self.p.stage(stage)["revision"]
            self.p.set_status(stage, "needs_modification", feedback=feedback)
            if was_approved:
                self.p.invalidate_downstream(stage)
        return self._append(stage, "modify", rev, feedback, actor)

    def _resubmit_approved(self, stage, artifact, actor):
        self.p.set_status(stage, "needs_modification")        # يرفع الاعتماد القديم أولاً
        self.p.invalidate_downstream(stage)
        # بعد invalidated لا تُحجب submit للمرحلة نفسها لأن ما قبلها ما زال مجتازاً
        return self.p.submit(stage, artifact, author=actor, note="human modification of approved stage")

    def regenerate_section(self, stage, actor, section, feedback):
        self._need(stage, "awaiting_approval", "approved", "rejected")
        art = self.p.artifact(stage)
        try:
            get_path(art, section)
        except (KeyError, IndexError, TypeError):
            raise ApprovalError(f"section '{section}' not found in {stage} r{self.p.stage(stage)['revision']}")
        was_approved = self.p.status(stage) == "approved"
        rec = self._append(stage, "regenerate_section", self.p.stage(stage)["revision"], feedback, actor, section)
        self.p.set_status(stage, "needs_regeneration", section=section, feedback=feedback)
        if was_approved:
            self.p.invalidate_downstream(stage)
        return rec

    def apply_section(self, stage, section, new_value, author="agent"):
        """يستبدل مقطعاً واحداً من آخر مراجعة ويُنشئ مراجعة جديدة (الباقي لا يتغير)."""
        self._need(stage, "needs_regeneration")
        art = json.loads(json.dumps(self.p.artifact(stage)))
        set_path(art, section, new_value)
        return self.p.submit(stage, art, author=author, note=f"regenerated section {section}")

    def rewind(self, to_stage, actor, reason):
        if not reason or not reason.strip():
            raise ApprovalError("reason is required")
        W.index(to_stage)
        rev = self.p.stage(to_stage)["revision"]
        rec = self._append(to_stage, "rewind", rev, reason, actor)
        self.p.set_status(to_stage, "invalidated", rewound_reason=reason)
        self.p.invalidate_downstream(to_stage)
        return rec

    def compare(self, stage, rev_a, rev_b):
        return diff(self.p.artifact(stage, rev_a), self.p.artifact(stage, rev_b))

    def resume(self):
        """ما الذي يجب فعله الآن؟ يعيد {stage, status, action}."""
        sid = self.p.next_stage()
        if sid is None:
            return {"stage": None, "status": "complete", "action": "project complete"}
        st = self.p.status(sid)
        action = {"pending": "run stage", "invalidated": "re-run stage (upstream changed)",
                  "awaiting_approval": f"human approval needed for r{self.p.stage(sid)['revision']}",
                  "rejected": "revise per feedback and resubmit", "needs_modification": "revise per feedback and resubmit",
                  "needs_regeneration": f"regenerate section {self.p.stage(sid).get('section')}",
                  "failed": "inspect failure, fix input, retry", "awaiting_output": "waiting for host task result"}.get(st, st)
        return {"stage": sid, "status": st, "action": action}
