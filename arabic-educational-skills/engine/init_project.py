#!/usr/bin/env python3
"""ينشئ مشروعاً جاهزاً للتصيير: python init_project.py <مجلد المشروع>
ينسخ الخطوط إلى assets/fonts (القالب يقرأها من ../../assets/fonts نسبةً إلى <مجلد الفيديو>/build)."""
import json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
(root / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
for f in (here / "fonts").glob("*.woff2"):
    shutil.copy2(f, root / "assets" / "fonts" / f.name)
cfg = root / "project-config.json"
if not cfg.exists():
    cfg.write_text(json.dumps({"version": "1.0.0", "videos": []}, ensure_ascii=False, indent=2) + "\n", "utf-8")
for sub in ("characters", "audio", "exports"):
    (root / sub).mkdir(exist_ok=True)
print("جاهز:", root, "\nضع كل فيديو في مجلد داخله (مثل video-01/) وفيه master-script.json")
