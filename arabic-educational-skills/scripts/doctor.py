#!/usr/bin/env python3
"""فحص البيئة قبل الإنتاج: python doctor.py
يطبع ما المتاح وما الناقص وأمر تثبيته. لا يثبّت شيئاً بنفسه."""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ok_all = True


def row(name, ok, fix=""):
    global ok_all
    ok_all &= ok
    print(("✓ " if ok else "✗ ") + name + ("" if ok else f"  ← {fix}"))


row("Python ≥ 3.9", sys.version_info >= (3, 9), "حدّث Python")
row("ffmpeg", bool(shutil.which("ffmpeg")), "apt install ffmpeg  أو  brew install ffmpeg")
row("ffprobe", bool(shutil.which("ffprobe")), "يأتي مع ffmpeg")
row("jsonschema", importlib.util.find_spec("jsonschema") is not None, "pip install jsonschema")
pw = importlib.util.find_spec("playwright") is not None
row("playwright (Python)", pw, "pip install playwright && playwright install chromium")
if pw:
    r = subprocess.run([sys.executable, "-c", (
        "from playwright.sync_api import sync_playwright\n"
        "import sys; sys.path.insert(0, %r)\n"
        "from render_scene import launch\n"
        "with sync_playwright() as p: b = launch(p); b.close()") % str(SKILL / "engine")],
        capture_output=True, text=True)
    row("متصفح Chromium يعمل", r.returncode == 0, "playwright install chromium  (" + (r.stderr.strip().splitlines() or [""])[-1][:120] + ")")
fonts = list((SKILL / "engine" / "fonts").glob("*.woff2"))
row(f"خطوط القالب ({len(fonts)})", len(fonts) >= 2, "الحزمة ناقصة: engine/fonts")
# محرك 4.0 (Remotion)
node = shutil.which("node")
nv = subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip() if node else ""
row(f"Node.js ≥ 18 ({nv or 'غير موجود'})", bool(nv) and int(nv.lstrip("v").split(".")[0]) >= 18, "ثبّت Node.js 18 أو أحدث")
rm = (SKILL / "remotion" / "node_modules" / "remotion").exists()
print(("✓ " if rm else "• ") + "اعتماديات Remotion" + ("" if rm else "  ← تُثبَّت تلقائياً عند أول `plan render` (npm install داخل remotion/)"))
print("\nالمحرك جاهز للتصيير" if ok_all else "\nأكمل الناقص أو اعرض على المستخدم بديلاً (سيناريو + حزمة صوت فقط بلا تصيير)")
sys.exit(0 if ok_all else 1)
