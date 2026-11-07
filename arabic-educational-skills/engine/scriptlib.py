"""أدوات لتوليد السيناريو الرئيسي (JSON + Markdown) من تعريف Python واحد.
text_plain يُشتق آلياً من text_diacritized (مصدر حقيقة واحد).
مثال:
    import sys; sys.path.insert(0, "<المهارة>/engine")
    from scriptlib import *
    doc = {..., "scenes": [scene("scene_01", 8, "هدف", ["teacher"], [d("teacher", "...", 1, 4)], [txt("...", 1, 8)])]}
    write_outputs(doc, Path("video-01"))"""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from aes_common import HARAKAT, TATWEEL  # noqa: E402
NOUN, PRED = "اسم إن (أزرق)", "خبر إن (أخضر)"


def plain(s):
    return "".join(c for c in s if c not in HARAKAT and c != TATWEEL)


def d(ch, text, start, end, emotion=None, tts=None, id=None):
    x = {"character": ch, "text_diacritized": text, "text_plain": plain(text), "start": start, "end": end}
    if id:
        x["id"] = id
    if tts:
        x["tts_text"] = tts  # فقط إن اختلف النطق عن المعروض (أعداد مكتوبة حروفاً مثلاً)
    if emotion:
        x["emotion"] = emotion
    return x


def scene(id, duration, goal, characters, dialogue, visuals, background="classroom", camera="ثابتة",
          enter=None, transition=None):
    x = {"id": id, "duration_seconds": duration, "learning_goal": goal, "background": background, "camera": camera,
         "characters": characters, "dialogue": dialogue, "visuals": visuals}
    if enter:
        x["enter"] = enter
    if transition:
        x["transition"] = transition
    return x


def txt(text, start, end, status=None, note=None):
    x = {"type": "arabic_text", "text_diacritized": text, "text_plain": plain(text),
         "direction": "rtl", "start": start, "end": end}
    if status:
        x["status"] = status  # wrong | right
    if note:
        x["note"] = note
    return x


def hl(text, role, start, end, tag=None):
    x = {"type": "highlight", "text_diacritized": text, "text_plain": plain(text),
         "color_role": role, "start": start, "end": end}
    if tag:
        x["tag"] = tag
    return x


def anim(note, start, end):
    return {"type": "animation", "note": note, "start": start, "end": end}


def badge(kind, start, end):
    return {"type": "badge", "kind": kind, "start": start, "end": end}


def callout(a, b, start, end, label_a, label_b):
    return {"type": "callout", "from_mark": a, "to_mark": b, "start": start, "end": end,
            "label_from": label_a, "label_to": label_b}


def quiz(start, end, options, answer, countdown_from, reveal, layout="rows", prompt=None):
    x = {"type": "quiz", "start": start, "end": end, "layout": layout,
         "options": [{"text_diacritized": o, "text_plain": plain(o)} for o in options],
         "answer_index": answer, "countdown_from": countdown_from, "reveal": reveal}
    if prompt:
        x["prompt_diacritized"] = prompt
        x["prompt_plain"] = plain(prompt)
    return x


LEVEL_LABEL = {"child": "طفل 6–9", "beginner": "ناشئ 10–13", "intermediate": "مراهق 14–17", "advanced": "جامعي/بالغ"}


def write_outputs(doc, out: Path, notes=None, audience=None):
    audience = audience or LEVEL_LABEL.get(doc.get("target_level"), doc.get("target_level", ""))
    out.mkdir(parents=True, exist_ok=True)
    (out / "master-script.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    scenes = doc["scenes"]
    total = sum(s["duration_seconds"] for s in scenes)
    names = {c["id"]: c["name"] for c in doc["characters"]}
    L = [f"# {doc['lesson']}", ""]
    L.append(f"- **الفئة:** {audience}  |  **المدة:** {total} ثانية (≈ {total/60:.1f} دقيقة)  |  **النسبة:** 16:9")
    L.append("- **الأسلوب:** " + doc.get("style", "—"))
    L.append("- **الأهداف:**")
    L += [f"  - {o}" for o in doc["objectives"]]
    L.append("- **الشخصيات:** " + "، ".join(f"{c['name']} ({c.get('role', '')})" for c in doc["characters"]))
    if doc.get("references"):
        L.append("- **المراجع:** " + "؛ ".join(f"[{r['id']}] {r['citation']}" for r in doc["references"]))
    L.append("")
    for s in scenes:
        L.append(f"## {s['id']} — {s['duration_seconds']} ث — {s['learning_goal']}")
        L.append(f"*الخلفية:* {s.get('background', '—')} | *الكاميرا:* {s.get('camera', '—')}")
        L += ["", "**الحوار**"]
        for x in s["dialogue"]:
            L.append(f"- [{x['start']}–{x['end']}] **{names[x['character']]}:** {x['text_diacritized']}")
        L += ["", "**المرئيات**"]
        for v in s["visuals"]:
            t = v["type"]
            if t in ("arabic_text", "highlight"):
                extra = f" ← {v['color_role']}" if t == "highlight" else (f" [{v['status']}]" if v.get("status") else "")
                L.append(f"- [{v['start']}–{v['end']}] نص: {v['text_diacritized']}{extra}")
            elif t == "quiz":
                opts = " | ".join(o["text_diacritized"] for o in v["options"])
                L.append(f"- [{v['start']}–{v['end']}] سؤال: {opts} ← الإجابة: {v['options'][v['answer_index']]['text_diacritized']}")
            elif t == "badge":
                L.append(f"- [{v['start']}–{v['end']}] شارة: {'✗' if v['kind'] == 'wrong' else '✓'}")
            elif t == "callout":
                L.append(f"- [{v['start']}–{v['end']}] لافتة: {v['label_from']} ← {v['label_to']}")
            else:
                L.append(f"- [{v['start']}–{v['end']}] {t}: {v.get('note', '')}")
        L.append("")
    L.append("## ملاحظات التنفيذ")
    L.append("- النص العربي يُركَّب برمجياً بخط Noto Sans Arabic، ولا يُولَّد داخل الصور.")
    L.append("- بعد كل سؤال في التمرين وقفة تفكير نحو 3 ثوانٍ بعدّاد تنازلي قبل ظهور الإجابة.")
    if not doc.get("references"):
        L.append("- القواعد والأمثلة لم تُراجَع بمرجع خارجي؛ تُدقَّق من معلم قبل النشر.")
    for n in notes or []:
        L.append("- " + n)
    (out / "master-script.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return total
