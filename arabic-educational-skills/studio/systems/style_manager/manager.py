"""مدير الأنماط: إنشاء/تعديل/تكرار/حذف/استيراد/تصدير/معاينة/حفظ مخصّص/دمج متوافق. المدمجة لا تُحذف ولا تُعدَّل (تُكرَّر)."""
import json
import re
from pathlib import Path

from .presets import COMPAT, PRESETS

REQUIRED = ("id", "name_ar", "name_en", "family", "visual_instructions", "requirements", "compatible_engines", "asset_requirements")
FAMILIES = {"cartoon", "cinematic", "motion", "scientific", "hybrid"}
SUPPORT = {"native", "partial", "provider_required"}
ID_RE = re.compile(r"^[a-z0-9_\-\+]+$")


class StyleError(ValueError):
    pass


def validate_style(s):
    errs = [f"missing '{k}'" for k in REQUIRED if k not in s or s[k] in ("", None)]
    if s.get("id") and not ID_RE.match(s["id"]):
        errs.append("id must match [a-z0-9_-+]")
    if s.get("family") and s["family"] not in FAMILIES:
        errs.append(f"family must be one of {sorted(FAMILIES)}")
    if s.get("render_support", "provider_required") not in SUPPORT:
        errs.append(f"render_support must be one of {sorted(SUPPORT)}")
    for k in ("requirements", "compatible_engines", "asset_requirements"):
        if k in s and not isinstance(s[k], list):
            errs.append(f"'{k}' must be a list")
    return errs


class StyleManager:
    def __init__(self, store_dir=None):
        self.dir = Path(store_dir) if store_dir else None
        self.builtin = {p["id"]: json.loads(json.dumps(p)) for p in PRESETS}
        self.custom = {}
        if self.dir and self.dir.exists():
            for f in sorted(self.dir.glob("*.json")):
                s = json.loads(f.read_text("utf-8"))
                self.custom[s["id"]] = s

    # ---------- استعلام
    def all(self):
        return {**self.builtin, **self.custom}

    def get(self, sid):
        try:
            return self.all()[sid]
        except KeyError:
            raise StyleError(f"unknown style '{sid}'. available: {sorted(self.all())}")

    def list_ids(self):
        return sorted(self.all())

    def _save(self, s):
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / f"{s['id']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), "utf-8")

    # ---------- CRUD
    def create(self, spec):
        s = {"builtin": False, "render_support": "provider_required", "palette": [], "suitable_ages": [], "notes": "",
             "combinable_with": [], **json.loads(json.dumps(spec))}
        s["builtin"] = False
        errs = validate_style(s)
        if errs:
            raise StyleError("; ".join(errs))
        if s["id"] in self.all():
            raise StyleError(f"style '{s['id']}' already exists")
        self.custom[s["id"]] = s
        self._save(s)
        return s

    def edit(self, sid, **changes):
        if sid in self.builtin:
            raise StyleError(f"'{sid}' is built-in and read-only; duplicate it first")
        s = {**self.get(sid), **changes, "id": sid, "builtin": False}
        errs = validate_style(s)
        if errs:
            raise StyleError("; ".join(errs))
        self.custom[sid] = s
        self._save(s)
        return s

    def duplicate(self, sid, new_id, **changes):
        base = json.loads(json.dumps(self.get(sid)))
        base.update(changes)
        base["id"], base["builtin"] = new_id, False
        base.setdefault("notes", "")
        return self.create(base)

    def delete(self, sid):
        if sid in self.builtin:
            raise StyleError(f"'{sid}' is built-in and cannot be deleted")
        self.get(sid)
        del self.custom[sid]
        if self.dir and (self.dir / f"{sid}.json").exists():
            (self.dir / f"{sid}.json").unlink()

    # ---------- استيراد/تصدير
    def export(self, sid, path):
        Path(path).write_text(json.dumps(self.get(sid), ensure_ascii=False, indent=2), "utf-8")

    def import_file(self, path, overwrite=False):
        s = json.loads(Path(path).read_text("utf-8"))
        if s.get("id") in self.builtin:
            raise StyleError("cannot import over a built-in style id")
        if overwrite and s.get("id") in self.custom:
            self.delete(s["id"])
        return self.create(s)

    # ---------- دمج
    def compatible(self, a, b):
        self.get(a), self.get(b)
        return (a, b) in COMPAT or (b, a) in COMPAT

    def combine(self, a, b, new_id=None, force=False):
        """نمط هجين: يتطلب توافقاً معلناً (أو force=True). الأساس هو الأول والثاني يضيف طبقة."""
        if not force and not self.compatible(a, b):
            raise StyleError(f"'{a}' and '{b}' are not declared compatible (use force=True to override at your own risk)")
        A, B = self.get(a), self.get(b)
        support = "native" if A["render_support"] == B["render_support"] == "native" else \
            "partial" if "native" in (A["render_support"], B["render_support"]) or "partial" in (A["render_support"], B["render_support"]) else "provider_required"
        h = {"id": new_id or f"{a}+{b}", "name_ar": f"{A['name_ar']} + {B['name_ar']}", "name_en": f"{A['name_en']} + {B['name_en']}",
             "family": "hybrid", "render_support": "provider_required" if support != "native" else "native",
             "requirements": list(dict.fromkeys(A["requirements"] + B["requirements"])),
             "visual_instructions": f"الأساس: {A['visual_instructions']} | الطبقة الإضافية: {B['visual_instructions']}",
             "compatible_engines": sorted(set(A["compatible_engines"]) | set(B["compatible_engines"])),
             "asset_requirements": list(dict.fromkeys(A["asset_requirements"] + B["asset_requirements"])),
             "palette": A["palette"][:2] + B["palette"][:2], "suitable_ages": sorted(set(A["suitable_ages"]) & set(B["suitable_ages"])),
             "notes": "هجين: " + ("؛ ".join(x for x in (A["notes"], B["notes"]) if x)), "combined_from": [a, b]}
        return self.create(h)

    # ---------- معاينة
    def preview(self, sid):
        """معاينة نصية صادقة: ما الذي سيُنتَج فعلاً وما الذي يحتاج مزوّداً."""
        s = self.get(sid)
        return {"id": s["id"], "name_ar": s["name_ar"], "palette": s["palette"], "render_support": s["render_support"],
                "can_render_locally": s["render_support"] == "native",
                "message": {"native": "يُصيَّر محلياً بمحرك المهارة.",
                            "partial": "يُصيَّر جزئياً محلياً؛ راجع notes لما ينقص.",
                            "provider_required": "مواصفة فقط: يلزم مزوّد صور/فيديو يختاره المستخدم؛ لا تُنتَج لقطات بدونه."}[s["render_support"]],
                "requirements": s["requirements"], "notes": s["notes"]}

    def preview_html(self, sid):
        p, s = self.preview(sid), self.get(sid)
        sw = "".join(f'<span style="display:inline-block;width:64px;height:64px;background:{c};border-radius:12px;margin:4px"></span>' for c in s["palette"])
        li = "".join(f"<li>{r}</li>" for r in s["requirements"])
        return (f'<!doctype html><meta charset="utf-8"><body dir="rtl" style="font-family:sans-serif;padding:24px">'
                f'<h2>{s["name_ar"]} <small>({s["name_en"]})</small></h2><p>{p["message"]}</p><div>{sw}</div>'
                f'<p>{s["visual_instructions"]}</p><ul>{li}</ul></body>')
