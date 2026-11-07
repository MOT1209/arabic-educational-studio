"""أدوات مشتركة بين سكربتات المهارة والمحرك (مكتبة قياسية فقط)."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CAPS_PATH = SKILL_DIR / "engine" / "capabilities.json"

# الحركات والتنوين والشدة والسكون والألف الخنجرية والهمزات/المدة المركّبة
HARAKAT = set("ًٌٍَُِّْٰٕٓٔ")
SHORT_VOWELS = "ً-ِْ"  # كل الحركات عدا الشدة
TATWEEL = "ـ"
HAS_ARABIC = re.compile(r"[؀-ۿ]")
# حروف فارسية/أردية تشبه العربية وتسبب أخطاء نطق وبحث
LOOKALIKES = {"ی": "ي", "ک": "ك", "ہ": "ه", "ے": "ي", "ھ": "ه"}


def strip_diacritics(s: str) -> str:
    s = s.replace(TATWEEL, "")
    return "".join(ch for ch in s if ch not in HARAKAT)


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", strip_diacritics(s)).strip()


def text_sha(s: str) -> str:
    return hashlib.sha256(unicodedata.normalize("NFC", s or "").encode("utf-8")).hexdigest()[:10]


def scene_hash(scene: dict) -> str:
    data = {k: v for k, v in scene.items() if k != "hash"}
    blob = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def line_id(scene: dict, index1: int, line: dict) -> str:
    """معرّف سطر الحوار: الحقل id إن وُجد (ثابت عند الإدراج/الحذف)، وإلا رقم الترتيب."""
    return line.get("id") or f"{scene['id']}_{index1:02d}"


def load_caps() -> dict:
    return json.loads(CAPS_PATH.read_text("utf-8"))


def load_json(path) -> dict:
    return json.loads(Path(path).read_text("utf-8"))


def write_json(path, doc) -> None:
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
