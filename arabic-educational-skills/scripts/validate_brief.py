#!/usr/bin/env python3
"""python validate_brief.py video-brief.json  — يتحقق من الملخص قبل كتابة السيناريو."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.core.schema import validate as _builtin_validate  # المدقق المدمج: لا حاجة لـ jsonschema
schema = json.loads((Path(__file__).resolve().parent.parent / "references" / "video-brief.schema.json").read_text("utf-8"))
brief = json.loads(Path(sys.argv[1]).read_text("utf-8"))
msgs = _builtin_validate(brief, schema)
if brief.get("style") in ("cinematic", "hybrid"):
    msgs.append("style: السينمائي/الهجين يحتاجان مزوّد صور/فيديو يوافق عليه المستخدم؛ غير متاح افتراضياً")
if not brief.get("approved"):
    msgs.append("approved: الملخص غير معتمد بعد؛ لا تنتقل إلى السيناريو")
if msgs:
    print("\n".join("✗ " + m for m in msgs)); sys.exit(1)
print("نجح التحقق: الملخص صالح ومعتمد")
