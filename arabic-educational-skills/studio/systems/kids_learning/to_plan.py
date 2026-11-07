"""يحوّل درس الحرف (alphabet.build_letter_lesson) إلى خطة درس عامة (lesson-plan v1) يصيّرها محرك Remotion.
درس الحرف صار قالباً واحداً من قوالب المهارة؛ المحرك نفسه يصيّر أي خطة في أي مادة."""
from .i18n import t

POS_HEAD = {"initial": "فِي أَوَّلِ الْكَلِمَةِ", "medial": "فِي وَسَطِ الْكَلِمَةِ", "final": "فِي آخِرِ الْكَلِمَةِ"}


def lesson_to_plan(lesson, *, formats=("16:9", "9:16"), theme="classroom", avatar_letter=None):
    letter, lang = lesson["letter"], lesson["lang"]
    age = "preschool" if lesson.get("profile") == "preschool" else "child"
    qby = {q["id"]: q for q in lesson["quiz"]}
    blocks, units, i = [], lesson["units"], 0
    n = 0

    def nid():
        nonlocal n
        n += 1
        return f"b{n:02d}"

    while i < len(units):
        u = units[i]
        ty, d = u["type"], u["display"]
        nxt = units[i + 1] if i + 1 < len(units) else None
        if ty == "intro":
            blocks.append({"id": nid(), "type": "title", "heading": f"حَرْفُ {lesson['name']}", "subheading": letter,
                           "narration": u["text"]})
        elif ty == "letter_card":
            blocks.append({"id": nid(), "type": "letter", "letter": letter, "name": lesson["name"], "trace": True,
                           "narration": u["text"]})
        elif ty == "forms":
            blocks.append({"id": nid(), "type": "letter", "letter": letter, "name": lesson["name"], "trace": False,
                           "show_forms": True, "narration": u["text"]})
        elif ty in ("sound", "syllable", "repeat"):
            syl = d.get("syllable", letter)
            blocks.append({"id": nid(), "type": "say_with_me", "text": syl, "narration": u["text"] if ty != "repeat" else None,
                           "cue": t(lang, "cue_say_with_me")})
        elif ty in ("position_intro", "reading_intro", "syllables_intro", "sentence_intro", "quiz_intro"):
            head = POS_HEAD.get(d.get("position"), "") or {"reading_intro": "نَقْرَأُ مَعًا", "syllables_intro": "الْحَرَكَاتُ",
                                                             "sentence_intro": "جُمْلَةٌ", "quiz_intro": "تَمْرِينٌ"}.get(ty, "")
            blocks.append({"id": nid(), "type": "explain", "heading": head, "narration": u["text"]})
        elif ty in ("word", "sukun"):
            b = {"id": nid(), "type": "word", "word": d["word"], "highlight_letters": d.get("letter_highlight", []),
                 "narration": u["text"], "hold_seconds": u["pause_seconds"] if u["repeat"] else 0,
                 "cue": t(lang, "cue_say_with_me") if u["repeat"] else None}
            if u.get("picture"):
                b["concept"] = u["picture"]["concept_en"]
            if nxt and nxt["type"] == "connection":
                b["narration_after"] = nxt["text"]
                i += 1
            blocks.append({k: v for k, v in b.items() if v not in (None, 0)})
        elif ty == "read":
            b = {"id": nid(), "type": "word", "word": d["word"], "highlight_letters": d.get("letter_highlight", []),
                 "syllables": d.get("syllables", []), "narration": u["text"], "delivery": "slow"}
            if nxt and nxt["type"] == "read" and nxt["display"].get("word") == d["word"]:
                b["narration_after"] = nxt["text"]
                b["hold_seconds"] = nxt["pause_seconds"]
                b["cue"] = t(lang, "cue_say_with_me")
                i += 1
            blocks.append(b)
        elif ty == "sentence":
            toks = d.get("tokens", [])
            hl = [toks[h["token"]] for h in d.get("highlights", []) if h["token"] < len(toks)]
            blocks.append({"id": nid(), "type": "example", "text": d["sentence"], "highlight": hl, "narration": u["text"],
                           "delivery": "slow", "hold_seconds": u["pause_seconds"]})
        elif ty == "contrast":
            ex = d.get("examples", [])
            blocks.append({"id": nid(), "type": "compare", "heading": "ا ≠ ى",
                           "right": {"label": "أَلِف", "text": ex[0] if ex else "ا", "status": "neutral"},
                           "left": {"label": "أَلِف مَقْصُورَة", "text": ex[1] if len(ex) > 1 else "ى", "status": "neutral"},
                           "narration": u["text"]})
        elif ty == "quiz":
            q = qby[d["quiz_id"]]
            ans = nxt if nxt and nxt["type"] == "answer" else None
            if q["kind"] == "where_in_word":
                opts = [t(lang, f"opt_{p}") for p in q["options"]]
                question = u["text"]
            else:
                opts = list(q["options"])
                question = t(lang, "q_sound_prompt") if q["kind"] == "sound_choice" else u["text"]
            b = {"id": nid(), "type": "quiz", "question": question, "options": opts,
                 "answer_index": q["options"].index(q["answer"]), "narration": u["text"],
                 "listening": q["kind"] == "sound_choice"}
            if q["kind"] == "sound_choice":
                b["caption_override"] = t(lang, "q_sound_caption")
            if ans:
                b["answer_narration"] = ans["text"]
                i += 1
            blocks.append(b)
        elif ty == "closing":
            blocks.append({"id": nid(), "type": "outro", "text": "أَحْسَنْتُمْ!", "subtext": f"حَرْفُ {lesson['name']}",
                           "narration": u["text"]})
        i += 1
    return {"plan_version": "1.0", "slug": f"letter-{ord(letter):04x}", "title": f"حَرْفُ {lesson['name']}",
            "subject": "arabic_letters", "audience": {"age_band": age, "lang": lang},
            "formats": list(formats), "style": {"theme": theme},
            "narrator": {"avatar": "letter_buddy", "avatar_letter": avatar_letter or letter},
            "source": {"generator": "kids_learning.alphabet", "profile": lesson.get("profile"),
                       "review_pending": len(lesson["review"]["needs_human_review"])},
            "blocks": blocks}
