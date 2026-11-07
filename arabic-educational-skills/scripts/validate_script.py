#!/usr/bin/env python3
"""يتحقق من السيناريو الرئيسي: السكيما + قواعد النص العربي + التوقيت + توافق المحرك + بنية تربوية.

الاستخدام:
    python validate_script.py master-script.json
    python validate_script.py master-script.json --update-hashes   # يحدّث البصمات ويثبّت معرّفات الأسطر
    python validate_script.py master-script.json --no-engine       # لسيناريو لن يُصيَّر بالمحرك المرفق

الأخطاء توقف العمل؛ التحذيرات تُراجَع وتُذكر للمستخدم إن بقيت.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aes_common import (HARAKAT, HAS_ARABIC, LOOKALIKES, SHORT_VOWELS, SKILL_DIR, TATWEEL,  # noqa: E402
                        line_id, load_caps, norm, scene_hash, write_json)

SCHEMA_PATH = SKILL_DIR / "references" / "master-script.schema.json"
DOUBLE_VOWEL = re.compile(f"[{SHORT_VOWELS}][{SHORT_VOWELS}]")
DOUBLE_SHADDA = re.compile("ّ[ً-ِْ]?ّ")
LATIN = re.compile(r"[A-Za-z]")
# مدى المدة الكلية (ثوانٍ) لكل مستوى — مأخوذ من references/audience-profiles.md
LEVEL_DURATION = {"child": (90, 240), "beginner": (150, 330), "intermediate": (210, 450), "advanced": (300, 780)}
AGE_TO_LEVEL = {"child": "child", "preteen": "beginner", "teen": "intermediate", "adult": "advanced"}
WORDS_PER_SEC = 2.6  # نطق تعليمي مشكول متمهّل؛ أسرع من هذا يُعدّ مستعجلاً


def check_text(path, diac, plain, errors, warnings):
    if not diac:
        return
    if plain is not None and norm(diac) != norm(plain):
        errors.append(f"{path}: text_plain لا يطابق text_diacritized بعد إزالة التشكيل")
    if HAS_ARABIC.search(diac) and not any(ch in HARAKAT for ch in diac) \
            and any(len(HAS_ARABIC.findall(w)) > 1 for w in diac.split()):  # حروف مفردة (بطاقة حرف/مقارنة) لا تحتاج تشكيلاً
        warnings.append(f"{path}: النص العربي بلا تشكيل")
    if DOUBLE_VOWEL.search(diac):
        errors.append(f"{path}: حركتان على حرف واحد (تحقق من التشكيل)")
    if DOUBLE_SHADDA.search(diac):
        errors.append(f"{path}: شدة مكررة على حرف واحد")
    if TATWEEL in diac:
        warnings.append(f"{path}: يحتوي تطويلاً (ـ)")
    bad = sorted({c for c in diac if c in LOOKALIKES})
    if bad:
        errors.append(f"{path}: حروف فارسية/أردية بدل العربية: " + "، ".join(f"U+{ord(c):04X}→{LOOKALIKES[c]}" for c in bad))
    if LATIN.search(diac):
        warnings.append(f"{path}: حروف لاتينية داخل النص العربي (لفّها بـ <bdi> عند العرض)")


def overlaps(items):
    s = sorted(items, key=lambda x: x[0])
    return [(a, b) for a, b in zip(s, s[1:]) if b[0] < a[1] - 1e-6]


def engine_checks(doc, caps, errors, warnings):
    chars = caps["characters"]
    rendered, descr = set(caps["rendered_visuals"]), set(caps["descriptive_only_visuals"])
    w, h = caps["resolution"]
    out = doc.get("output", {})
    if (out.get("width"), out.get("height")) != (w, h):
        errors.append(f"محرك: يصيّر {w}x{h} فقط؛ output = {out.get('width')}x{out.get('height')}. "
                      "للمقاطع العمودية أعد تخطيط القالب أولاً (references/platforms.md)")
    for sc in doc.get("scenes", []):
        sid = sc.get("id")
        for c in sc.get("characters", []):
            if c not in chars:
                errors.append(f"محرك {sid}: الشخصية '{c}' غير مرسومة في القالب (المتاح: {', '.join(chars)}). "
                              "أضف رسمها أولاً أو استعمل شخصية متاحة")
        texts = [v for v in sc.get("visuals", []) if v.get("type") == "arabic_text"]
        for j, v in enumerate(sc.get("visuals", [])):
            p = f"محرك {sid}.visuals[{j}]"
            t = v.get("type")
            if t in descr:
                warnings.append(f"{p}: النوع '{t}' وصفي ولا يُرسم في المحرك الحالي")
            elif t not in rendered:
                warnings.append(f"{p}: النوع '{t}' غير مدعوم في المحرك")
            if t == "arabic_text" and len(v.get("text_diacritized", "").split()) > caps["board_max_words"]:
                warnings.append(f"{p}: أكثر من {caps['board_max_words']} كلمات على السبورة؛ سيُصغَّر الخط")
            if t == "highlight":
                hit = [x for x in texts if x["start"] <= v["start"] + 1e-6 and v["end"] <= x["end"] + 1e-6
                       and v.get("text_diacritized") in x.get("text_diacritized", "").split(" ")]
                if not hit:
                    errors.append(f"{p}: التلوين '{v.get('text_diacritized')}' لا يطابق كلمة كاملة (بتشكيلها) "
                                  "في نص arabic_text معروض طوال مدته؛ لن يظهر")
            if t == "quiz":
                opts = v.get("options", [])
                if len(opts) > caps["quiz"]["max_options"]:
                    errors.append(f"{p}: القالب يعرض {caps['quiz']['max_options']} خيارات كحد أقصى")
                for k in ("countdown_from", "reveal", "answer_index", "layout"):
                    if k not in v:
                        errors.append(f"{p}: quiz يحتاج الحقل {k}")
        for d in sc.get("dialogue", []):
            if d.get("emotion") and d["emotion"] not in caps["emotions"]:
                warnings.append(f"محرك {sid}: الانفعال '{d['emotion']}' لا تعبير له في القالب (المتاح: {'، '.join(caps['emotions'])})")


def semantic_checks(doc, errors, warnings):
    char_ids = {c["id"] for c in doc.get("characters", [])}
    ref_ids = {r["id"] for r in doc.get("references", [])}
    seen, line_ids = set(), set()
    for i, sc in enumerate(doc.get("scenes", [])):
        sid = sc.get("id", f"#{i}")
        if sid in seen:
            errors.append(f"{sid}: معرّف مشهد مكرر")
        seen.add(sid)
        dur = sc.get("duration_seconds", 0)
        for ch in sc.get("characters", []):
            if ch not in char_ids:
                errors.append(f"{sid}: شخصية غير معرّفة '{ch}'")
        spans = []
        if not sc.get("dialogue"):
            warnings.append(f"{sid}: مشهد بلا حوار (سيُصيَّر صامتاً)")
        for j, d in enumerate(sc.get("dialogue", []), 1):
            p = f"{sid}.dialogue[{j - 1}]"
            lid = line_id(sc, j, d)
            if lid in line_ids:
                errors.append(f"{p}: معرّف سطر مكرر '{lid}'")
            line_ids.add(lid)
            if d.get("character") not in char_ids:
                errors.append(f"{p}: شخصية غير معرّفة '{d.get('character')}'")
            elif sc.get("characters") and d["character"] not in sc["characters"]:
                warnings.append(f"{p}: '{d['character']}' يتكلم وهو غير حاضر في المشهد")
            s, e = d.get("start", 0), d.get("end", 0)
            if e <= s:
                errors.append(f"{p}: end يجب أن يكون بعد start")
            if e > dur + 1e-6:
                errors.append(f"{p}: يتجاوز مدة المشهد ({dur}s)")
            spans.append((s, e))
            spoken = d.get("tts_text") or d.get("text_diacritized", "")
            words = len(spoken.split())
            if e > s and words / (e - s) > WORDS_PER_SEC:
                warnings.append(f"{p}: {words} كلمات في {e - s:.1f}s — أسرع من النطق التعليمي؛ وسّع الوقت")
            check_text(p, d.get("text_diacritized"), d.get("text_plain"), errors, warnings)
            if d.get("tts_text") and d.get("tts_text") != d.get("text_diacritized"):
                warnings.append(f"{p}: tts_text يختلف عن النص المعروض؛ تأكد أن الفرق مقصود (أعداد/نطق)")
        for a, b in overlaps(spans):
            errors.append(f"{sid}: سطرا حوار متداخلان ({a[0]}–{a[1]} و {b[0]}–{b[1]})")
        for j, v in enumerate(sc.get("visuals", [])):
            p = f"{sid}.visuals[{j}]"
            if v.get("end", 0) <= v.get("start", 0):
                errors.append(f"{p}: end يجب أن يكون بعد start")
            if v.get("end", 0) > dur + 1e-6:
                errors.append(f"{p}: يتجاوز مدة المشهد ({dur}s)")
            if v.get("type") == "arabic_text":
                if not v.get("text_diacritized") or not v.get("text_plain"):
                    errors.append(f"{p}: arabic_text يحتاج text_diacritized و text_plain")
                if v.get("direction") != "rtl":
                    errors.append(f"{p}: direction يجب أن يكون rtl")
                words = len(v.get("text_diacritized", "").split())
                if words and (v["end"] - v["start"]) < 0.5 * words:
                    warnings.append(f"{p}: النص يبقى أقل من 0.5 ث لكل كلمة")
            check_text(p, v.get("text_diacritized"), v.get("text_plain"), errors, warnings)
            check_text(p + ".prompt", v.get("prompt_diacritized"), v.get("prompt_plain"), errors, warnings)
            for k, o in enumerate(v.get("options", []) or []):
                if isinstance(o, dict):
                    check_text(f"{p}.options[{k}]", o.get("text_diacritized"), o.get("text_plain"), errors, warnings)
            if v.get("type") == "quiz":
                opts = v.get("options") or []
                ai = v.get("answer_index", -1)
                if not 0 <= ai < len(opts):
                    errors.append(f"{p}: answer_index خارج الخيارات")
                cf, rv = v.get("countdown_from"), v.get("reveal")
                if cf is not None and rv is not None:
                    if not (v["start"] <= cf < rv <= v["end"]):
                        errors.append(f"{p}: يجب start ≤ countdown_from < reveal ≤ end")
                    elif rv - cf < 3 - 1e-6:
                        warnings.append(f"{p}: وقفة التفكير أقل من 3 ث قبل كشف الإجابة")
            ref = v.get("reference")
            if ref and ref not in ref_ids:
                errors.append(f"{p}: reference غير موجود '{ref}'")


def pedagogy_checks(doc, warnings):
    scenes = doc.get("scenes", [])
    vis = [v for s in scenes for v in s.get("visuals", [])]
    if not any(v.get("type") == "quiz" for v in vis):
        warnings.append("تربوي: لا يوجد تمرين (quiz) في الفيديو")
    letter_lesson = str(doc.get("meta", {}).get("generator", "")).startswith("kids_learning")
    if letter_lesson:  # درس حرف مولَّد: بنيته ثابتة (تعرّف→أمثلة→مقاطع→قراءة→جملة→تمرين)؛ فحوص الخطأ الشائع/الأهداف/المدة لا تنطبق
        return
    if not any(v.get("status") == "wrong" or v.get("kind") == "wrong" for v in vis):
        warnings.append("تربوي: لا يوجد مثال للخطأ الشائع (status/kind = wrong)")
    if len(doc.get("objectives", [])) > 2:
        warnings.append("تربوي: أكثر من هدفين؛ الأفضل مفهوم واحد لكل فيديو")
    total = sum(s.get("duration_seconds", 0) for s in scenes)
    lo, hi = LEVEL_DURATION.get(doc.get("target_level"), (0, 1e9))
    if total >= 60 and not lo <= total <= hi:  # دون 60 ث: مشهد تجريبي أو مقطع قصير
        warnings.append(f"تربوي: المدة {total:.0f}s خارج المدى المقترح للمستوى ({lo}–{hi}s)")


def brief_checks(script_path, doc, warnings):
    bp = Path(script_path).resolve().parent / "video-brief.json"
    if not bp.exists():
        return
    brief = json.loads(bp.read_text("utf-8"))
    age = brief.get("audience", {}).get("age_band")
    if age and AGE_TO_LEVEL.get(age) != doc.get("target_level"):
        warnings.append(f"الملخص: age_band={age} يقابله target_level={AGE_TO_LEVEL.get(age)} لا {doc.get('target_level')}")
    want = brief.get("format", {}).get("duration_seconds")
    total = sum(s.get("duration_seconds", 0) for s in doc.get("scenes", []))
    if want and abs(total - want) / want > 0.2:
        warnings.append(f"الملخص: المدة المعتمدة {want}s والسيناريو {total:.0f}s (فرق > 20%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--update-hashes", action="store_true")
    ap.add_argument("--no-engine", action="store_true", help="تخطَّ فحوص توافق المحرك المرفق")
    args = ap.parse_args()

    path = Path(args.script)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"خطأ في قراءة JSON: {e}")
        return 2

    errors, warnings = [], []
    try:
        import jsonschema  # type: ignore
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path)):
            errors.append(f"schema {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")
    except ImportError:  # المدقق المدمج يغطي المخطط كاملاً بلا اعتماديات
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from studio.core.schema import validate as builtin_validate
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        for e in builtin_validate(doc, schema):
            errors.append(f"schema {e}")

    if isinstance(doc.get("scenes"), list):
        semantic_checks(doc, errors, warnings)
        pedagogy_checks(doc, warnings)
        brief_checks(path, doc, warnings)
        if not args.no_engine:
            engine_checks(doc, load_caps(), errors, warnings)

    changed = []
    if args.update_hashes and not errors:
        for sc in doc["scenes"]:
            for j, d in enumerate(sc.get("dialogue", []), 1):
                d.setdefault("id", f"{sc['id']}_{j:02d}")  # تثبيت المعرّف قبل أي إدراج لاحق
            h = scene_hash(sc)
            if sc.get("hash") != h:
                changed.append(sc["id"])
            sc["hash"] = h
        write_json(path, doc)
        print("بصمات محدّثة؛ مشاهد تغيّرت:", ", ".join(changed) if changed else "لا شيء")
    elif not args.update_hashes:
        for sc in doc.get("scenes", []):
            if sc.get("hash") and sc["hash"] != scene_hash(sc):
                warnings.append(f"{sc.get('id')}: تغيّر المحتوى منذ آخر بصمة — شغّل --update-hashes ثم أعد إنتاجه")

    for w in warnings:
        print("تحذير:", w)
    for e in errors:
        print("خطأ:", e)
    if errors:
        print(f"فشل التحقق: {len(errors)} خطأ، {len(warnings)} تحذير")
        return 1
    print(f"نجح التحقق ({len(warnings)} تحذير)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
