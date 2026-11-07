"""مدير الأصول الدائم: شخصيات، مواقع، خلفيات، دعائم، صور، فيديو، صوت، موسيقى، خطوط، شعارات.
سجل assets/registry.json + نسخ ملفات مُرقَّمة بالإصدار + بصمة sha256 للتحقق من السلامة. لا حذف صامت."""
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

KINDS = ("character", "location", "background", "prop", "image", "video", "audio", "music", "font", "logo", "other")
ID_RE = re.compile(r"^[a-z0-9_\-]+$")


class AssetError(ValueError):
    pass


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class AssetManager:
    def __init__(self, root):
        self.root = Path(root)
        self.file = self.root / "registry.json"
        self.data = json.loads(self.file.read_text("utf-8")) if self.file.exists() else {"assets": {}}

    def _save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.file)

    def register(self, id, kind, name, source_file, *, description="", tags=(), license="", source="", character=None, note=""):
        if not ID_RE.match(id):
            raise AssetError("id must match [a-z0-9_-]+")
        if kind not in KINDS:
            raise AssetError(f"kind must be one of {KINDS}")
        if id in self.data["assets"]:
            raise AssetError(f"asset '{id}' exists; use add_version")
        if kind != "character" and character:
            raise AssetError("character spec only for kind=character")
        a = {"id": id, "kind": kind, "name": name, "description": description, "tags": sorted(set(tags)), "created": _now(),
             "approved": False, "versions": []}
        if character:
            a["character"] = character
        self.data["assets"][id] = a
        try:
            self.add_version(id, source_file, license=license, source=source, note=note)
        except Exception:
            del self.data["assets"][id]
            raise
        return a

    def add_version(self, id, source_file, *, license="", source="", note=""):
        a = self.get(id)
        src = Path(source_file)
        if not src.is_file():
            raise AssetError(f"source file not found: {src}")
        v = len(a["versions"]) + 1
        rel = Path(a["kind"]) / id / f"v{v:03d}_{src.name}"
        dst = self.root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        a["versions"].append({"version": v, "path": rel.as_posix(), "sha256": sha256_of(dst), "added": _now(), "note": note,
                              "license": license, "source": source})
        a["approved"] = False             # أي إصدار جديد يحتاج اعتماداً من جديد
        self._save()
        return v

    def get(self, id):
        if id not in self.data["assets"]:
            raise AssetError(f"unknown asset '{id}'")
        return self.data["assets"][id]

    def approve(self, id, actor):
        if not actor.strip():
            raise AssetError("actor required")
        a = self.get(id)
        a["approved"], a["approved_by"], a["approved_version"] = True, actor, a["versions"][-1]["version"]
        self._save()

    def path_of(self, id, version=None):
        a = self.get(id)
        v = a["versions"][(version or len(a["versions"])) - 1]
        return self.root / v["path"]

    def find(self, kind=None, tag=None, approved=None):
        return [a for a in self.data["assets"].values()
                if kind in (None, a["kind"]) and (tag is None or tag in a["tags"]) and (approved is None or a["approved"] == approved)]

    def verify(self):
        """يعيد مشاكل السلامة: ملف مفقود أو بصمة لا تطابق."""
        issues = []
        for a in self.data["assets"].values():
            for v in a["versions"]:
                p = self.root / v["path"]
                if not p.exists():
                    issues.append(f"{a['id']} v{v['version']}: file missing")
                elif sha256_of(p) != v["sha256"]:
                    issues.append(f"{a['id']} v{v['version']}: sha256 mismatch (file changed)")
        return issues

    def check_character_consistency(self, master_script, engine_caps):
        """يقارن شخصيات السيناريو بسجل الأصول وبما يرسمه المحرك فعلاً (الجنس خصوصاً: خطأ حدث فعلاً في v2)."""
        issues = []
        drawn = engine_caps.get("characters", {})
        for sc in master_script.get("scenes", []):
            for cid in sc.get("characters", []):
                rec = self.data["assets"].get(f"char_{cid}")
                if cid in drawn and rec and rec.get("character", {}).get("gender") not in (None, drawn[cid].get("gender")):
                    issues.append(f"{sc['id']}: character '{cid}' is {rec['character']['gender']} in the asset record but the engine draws {drawn[cid].get('gender')}")
                if cid not in drawn:
                    issues.append(f"{sc['id']}: character '{cid}' has no drawing in the engine template")
        return sorted(set(issues))
