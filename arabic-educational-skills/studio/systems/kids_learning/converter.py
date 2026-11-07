"""يحوّل درس الحرف (alphabet.build_letter_lesson) إلى سيناريو رئيسي master-script يقرؤه المحرك.
المشاهد: وحدة الكلمة تضم وحدة الاتصال، والسؤال يضم جوابه، وقراءتا البطيء/العادي معاً؛ والباقي مشهد لكل وحدة.
أنواع المرئيات المستعملة: arabic_text, letter_highlight, letter_card, image, quiz, cue, badge."""
from ...engines.script_engine import MIN_LINE
from .i18n import t

try:
    from engine.scriptlib import plain  # noqa: F401  (عند التشغيل من جذر المهارة)
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
    from scriptlib import plain  # type: ignore

VERSION = "1.0.0"
MERGE_INTO_PREV = {"connection": {"word"}, "answer": {"quiz"}}
PAIR = {"read": {"read"}}
EMOTION = {"intro": "مرح", "closing": "فرح", "answer": "تشجيع", "quiz": "تشويق", "contrast": "تشويق"}
OPT_KEY = {"initial": "opt_initial", "medial": "opt_medial", "final": "opt_final"}
UNIT_TITLES_AR = {"A": "التعرّف", "B": "أول الكلمة", "C": "وسط الكلمة", "D": "آخر الكلمة", "E": "المقاطع",
                  "F": "القراءة", "G": "الجملة", "H": "التمرين"}


def _group(units):
    groups = []
    for u in units:
        prev = groups[-1] if groups else None
        if prev and (prev[0]["type"] in MERGE_INTO_PREV.get(u["type"], ()) or
                     (u["type"] == "read" and prev[-1]["type"] == "read" and len(prev) < 2 and
                      prev[0]["display"].get("word") == u["display"].get("word"))):
            prev.append(u)
        else:
            groups.append([u])
    return groups


def _visuals_for(group, lesson, t0, t1, quiz_by_id):
    first = group[0]
    d, ty = first["display"], first["type"]
    letter = lesson["letter"]
    pic = first.get("picture")
    V = []
    if ty in ("intro", "letter_card"):
        V.append({"type": "letter_card", "letter": letter, "name": lesson["name"], "forms": lesson["forms"],
                  "text_diacritized": letter, "text_plain": letter, "start": t0, "end": t1})
    elif ty == "forms":
        V.append({"type": "letter_card", "letter": letter, "name": lesson["name"], "forms": lesson["forms"],
                  "show_forms": True, "text_diacritized": letter, "text_plain": letter, "start": t0, "end": t1})
    elif ty in ("sound", "repeat"):
        syl = d.get("syllable", letter)
        V.append({"type": "arabic_text", "text_diacritized": syl, "text_plain": plain(syl), "direction": "rtl",
                  "size": "xl", "start": t0, "end": t1})
        V.append({"type": "cue", "text": t(lesson["lang"], "cue_repeat"), "start": max(t0, t1 - 2.5), "end": t1})
    elif ty in ("word", "sukun") or (ty == "read" and d.get("word")):
        w = d["word"]
        V.append({"type": "letter_highlight", "text_diacritized": w, "text_plain": plain(w), "direction": "rtl",
                  "highlight_indices": d.get("letter_highlight", []), "letter": letter, "start": t0, "end": t1})
        if pic:
            V.append({"type": "image", "asset": f"concept:{pic['concept_en']}", "note": pic["concept_en"],
                      "illustrable": pic["illustrable"], "start": t0, "end": t1})
        if ty == "word" and first.get("repeat") and lesson.get("profile") == "preschool":
            V.append({"type": "cue", "text": t(lesson["lang"], "cue_say_with_me"), "start": max(t0, t0 + first["duration_seconds"] - 2.5),
                      "end": t0 + first["duration_seconds"]})
        if ty == "read" and len(d.get("syllables") or []) > 1:
            V.append({"type": "arabic_text", "text_diacritized": " ".join(d["syllables"]),
                      "text_plain": plain(" ".join(d["syllables"])), "direction": "rtl", "role": "syllables",
                      "start": t0 + (t1 - t0) * 0.35, "end": t1})
    elif ty == "syllable":
        s = d["syllable"]
        V.append({"type": "arabic_text", "text_diacritized": s, "text_plain": plain(s), "direction": "rtl",
                  "size": "xl", "start": t0, "end": t1})
        V.append({"type": "cue", "text": t(lesson["lang"], "cue_repeat"), "start": max(t0, t1 - 2.5), "end": t1})
    elif ty == "contrast":
        V.append({"type": "arabic_text", "text_diacritized": "ا ≠ ى", "text_plain": "ا ≠ ى", "direction": "rtl",
                  "size": "xl", "start": t0, "end": t1})
        for i, w in enumerate(d.get("examples", [])):
            V.append({"type": "arabic_text", "text_diacritized": w, "text_plain": plain(w), "direction": "rtl",
                      "role": "contrast_example", "start": t0 + (t1 - t0) * (0.4 + 0.2 * i), "end": t1})
    elif ty == "sentence":
        s = d["sentence"]
        V.append({"type": "arabic_text", "text_diacritized": s, "text_plain": plain(s), "direction": "rtl",
                  "highlight_tokens": d.get("highlights", []), "letter": letter, "start": t0, "end": t1})
    elif ty == "quiz":
        q = quiz_by_id[d["quiz_id"]]
        qtime = group[0]["duration_seconds"]
        if q["kind"] in ("which_starts_with", "sound_choice", "find_letter"):
            opts, ans = q["options"], q["options"].index(q["answer"])
        else:
            opts = [t(lesson["lang"], OPT_KEY[p]) for p in q["options"]]
            ans = q["options"].index(q["answer"])
        reveal_at = t0 + min(qtime, (t1 - t0) - 1.0)
        # سؤال الاستماع: لا يُكتب المقطع على السبورة كي لا تنكشف الإجابة
        prompt = t(lesson["lang"], "q_sound_prompt") if q["kind"] == "sound_choice" else first["text"]
        letter_opts = q["kind"] in ("sound_choice", "find_letter")
        V.append({"type": "quiz", "layout": "row" if letter_opts else "rows", "labels": "digits" if letter_opts else "letters", "options": [{"text_diacritized": o, "text_plain": plain(o)} for o in opts],
                  "answer_index": ans, "countdown_from": 3, "reveal": round(reveal_at, 2),
                  "prompt_diacritized": prompt, "prompt_plain": plain(prompt), "start": t0, "end": t1})
        V.append({"type": "badge", "kind": "right", "start": round(reveal_at, 2), "end": t1})
    elif ty == "closing":
        V.append({"type": "letter_card", "letter": letter, "name": lesson["name"], "forms": lesson["forms"],
                  "text_diacritized": letter, "text_plain": letter, "start": t0, "end": t1})
    else:
        V.append({"type": "letter_card", "letter": letter, "name": lesson["name"], "forms": lesson["forms"],
                  "text_diacritized": letter, "text_plain": letter, "start": t0, "end": t1})
    return V


def lesson_to_master_script(lesson, *, teacher_name="الأستاذ سامي", style="فصل كرتوني ملوّن للأطفال",
                            lesson_title=None):
    """يعيد dict يطابق master-script.schema.json. التوقيت مأخوذ من duration_seconds لكل وحدة."""
    letter, lang = lesson["letter"], lesson["lang"]
    quiz_by_id = {q["id"]: q for q in lesson["quiz"]}
    scenes, cursor = [], 0
    for gi, group in enumerate(_group(lesson["units"]), start=1):
        sid = f"scene_{gi:02d}"
        dur = round(sum(u["duration_seconds"] for u in group), 2)
        dialogue, t_local = [], 0.0
        for u in group:
            speech = u["speech_seconds"]
            start = round(t_local + 0.3, 2)
            end = round(start + max(MIN_LINE - 0.35, speech - 0.35), 2)
            did = f"u{ord(letter):04x}_{u['id']}"
            x = {"id": did, "character": "teacher", "text_diacritized": u["text"], "text_plain": plain(u["text"]),
                 "start": start, "end": min(end, round(t_local + u["duration_seconds"], 2)),
                 "emotion": EMOTION.get(u["type"], "مرح")}
            if u["repeat"]:
                x["pause_after_for_repeat"] = u["pause_seconds"]
            qd = quiz_by_id.get(u["display"].get("quiz_id")) if u["type"] == "quiz" else None
            if qd and qd["kind"] == "sound_choice":
                x["caption_text"] = t(lang, "q_sound_caption")
            dialogue.append(x)
            t_local += u["duration_seconds"]
        visuals = _visuals_for(group, lesson, 0.0, dur, quiz_by_id)
        scenes.append({"id": sid, "duration_seconds": dur, "learning_goal": f"{UNIT_TITLES_AR[group[0]['stage']]} — {letter}",
                       "stage": group[0]["stage"], "background": "classroom", "camera": "ثابتة", "characters": ["teacher"],
                       "dialogue": dialogue, "visuals": visuals,
                       "unit_ids": [u["id"] for u in group]})
        cursor += dur
    total = round(sum(s["duration_seconds"] for s in scenes), 2)
    doc = {"version": VERSION, "lesson": lesson_title or f"حرف {lesson['name']} ({letter})", "subject": "phonetics",
           "language": lang if lang == "ar" else ["ar", "en"], "target_level": "child",
           "objectives": [f"أن يتعرّف الطفل على حرف {lesson['name']} وأشكاله ومواضعه في الكلمة",
                          f"أن ينطق مقاطع {lesson['name']} بالحركات", "أن يقرأ كلمات وجملة تحتوي الحرف"],
           "style": style,
           "characters": [{"id": "teacher", "name": teacher_name, "role": "يقدّم الدرس"}],
           "output": {"width": 1920, "height": 1080, "fps": 30, "formats": ["16:9"]},
           "scenes": scenes,
           "meta": {"generator": "kids_learning.alphabet", "total_seconds": total, "letter": letter,
                    "review_pending": len(lesson["review"]["needs_human_review"]),
                    "all_content_approved": lesson["review"]["all_approved"]}}
    return doc
