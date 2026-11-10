"""مدير المزوّدين. صادق: لا يُعلن مزوّداً «implemented» إلا إن كان قابلاً للتشغيل فعلاً الآن.

- `local_engine` (render): محرك التصيير المحلي HTML/Remotion ← Playwright ← FFmpeg، مجاني.
- `local_tts` (speech): نموذج صوتي محلي تضيفه أنت عبر `AES_LOCAL_TTS_CMD` (انظر studio/providers/local_tts.py).
- بقية المزوّدين مواصفات فقط (not_implemented) حتى يُكتب لها تنفيذ حقيقي.
"""
import shutil

from studio.providers.local_tts import LocalTTSProvider


class ProviderNotImplemented(Exception):
    pass


def _external(pid, kind, caps, notes):
    return {"id": pid, "kind": kind, "status": "not_implemented", "capabilities": caps,
            "cost": {"unit": "call", "usd_per_unit": None}, "irreversible": False, "requires_network": True, "notes": notes}


class ProviderManager:
    def __init__(self, constraints=None, tts_config=None):
        self.constraints = constraints or {}
        self._tts = LocalTTSProvider(tts_config)

    # ---------- التسجيل ----------
    def _local_engine(self):
        ok = bool(shutil.which("ffmpeg"))
        return {"id": "local_engine", "kind": "render", "status": "implemented" if ok else "not_implemented",
                "capabilities": ["classroom_2d_cartoon", "lesson_plan_remotion", "subtitles"],
                "cost": {"unit": "scene", "usd_per_unit": 0.0}, "irreversible": False, "requires_network": False,
                "notes": "تصيير محلي مجاني" if ok else "ffmpeg غير موجود"}

    def _local_tts(self):
        ok, why = self._tts.check()
        return {"id": "local_tts", "kind": "speech", "status": "implemented" if ok else "not_implemented",
                "capabilities": ["speech:ar"], "cost": {"unit": "line", "usd_per_unit": 0.0}, "irreversible": False,
                "requires_network": False, "notes": "نموذج صوتي محلي: " + why}

    def list(self):
        return [self._local_engine(), self._local_tts(),
                _external("image_provider", "image", ["image"], "مولّد صور غير منفَّذ (ولا يصلح لنص عربي)"),
                _external("video_provider", "video", ["video"], "مولّد فيديو غير منفَّذ"),
                _external("speech_cloud", "speech", ["speech:ar"], "خدمة نطق سحابية غير منفَّذة؛ الصوت من تسجيل أو ElevenLabs Studio يدوياً")]

    def get(self, pid):
        for p in self.list():
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    def allowed(self, p):
        return not (self.constraints.get("no_external_providers") and p["requires_network"])

    # ---------- الاستعمال ----------
    def require(self, kind):
        """يعيد أول مزوّد منفَّذ ومسموح من هذا النوع، وإلا يرمي ProviderNotImplemented."""
        for p in self.list():
            if p["kind"] == kind and p["status"] == "implemented" and self.allowed(p):
                return p
        raise ProviderNotImplemented(f"لا مزوّد منفَّذ ومسموح لنوع '{kind}'")

    def synthesizer(self):
        """مزوّد النطق المحلي الجاهز، أو يرمي ProviderNotImplemented."""
        p = self.require("speech")
        if p["id"] != "local_tts":
            raise ProviderNotImplemented(f"المزوّد '{p['id']}' لا يملك تنفيذاً")
        return self._tts

    def estimate_item(self, pid, units):
        p = self.get(pid)
        return {"provider": pid, "units": units, "unit_cost_usd": p["cost"]["usd_per_unit"]}

    def health(self):
        return {p["id"]: {"ok": p["status"] == "implemented", "status": p["status"], "notes": p["notes"]} for p in self.list()}
