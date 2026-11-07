"""مولّد درس الحرف العربي (المراحل A–H). حتمي بالكامل: يختار أمثلة من البنك بعد فحصها إملائياً وموضعياً،
ويبني السرد من قوالب مشكولة، ويقدّر الزمن، ويصنّف ما يحتاج مراجعة بشرية.
لا يدّعي أن المحتوى «معتمد»: كل كلمة/جملة غير موقَّعة في ReviewLedger تظهر في review.needs_human_review."""
import hashlib
import unicodedata

from ..arabic_language import letters as L
from ..arabic_language.bank import MAKSURA_CONTRAST, BANK, words_for
from ..arabic_language.orthography import check_example
from ..arabic_language.sentences import build_sentence, check_sentence
from ..arabic_language.syllables import has_shadda, syllable_texts
from ...engines import script_engine as SE
from .i18n import LETTER_NAME_EN, t
from .levels import STAGE_LEVELS, STAGE_TITLES, assert_progression

SCHEMA_VERSION = "1.0"
HARD_SOUNDS = set("ثحخذصضطظعغق")
POS_KEY = {"initial": "B", "medial": "C", "final": "D"}
UNIT_MIN_VISUAL = 2.0          # أقل مدة للشاشة حتى لو كان الكلام أقصر

# ملفات تعريف الدرس. preschool = 4–6 سنوات: درس 2–3 دقائق، نداء وترديد («قُولُوا مَعِي»)، شرح الاتصال مرة
# واحدة لكل موضع، بلا كلمات مشددة في الأمثلة والقراءة (الشدة تُدرَّس لاحقاً)، وأربعة أنواع تمارين.
PROFILES = {
    "standard": {"examples": 3, "speech_factor": 1.0, "pause_extra": 0.0, "join_once": False, "call_response": False,
                 "allow_shadda": True, "quiz_items": 4, "read_words": 2, "default_target": None, "combos_n": (3, 2), "combos_r": (3, 2, 1), "repeat_cue": True,
                 "repeat_pause": None, "syllable_marks": None, "sukun": True},
    "preschool": {"examples": 2, "speech_factor": 1.15, "pause_extra": 0.6, "join_once": True, "call_response": True,
                  "allow_shadda": False, "quiz_items": 4, "read_words": 1, "default_target": 180, "combos_n": (2, 1), "combos_r": (1,), "repeat_cue": False,
                  # وقفة الترديد ثابتة: الطفل يردد الكلمة أو المقطع فقط، لا جملة الشرح كلها
                  "repeat_pause": 2.5, "syllable_marks": ("fatha", "kasra", "damma"), "sukun": False},
}
QUIZ_KINDS = ("which_starts_with", "where_in_word", "sound_choice", "find_letter")

# حروف متشابهة الرسم (للتمييز البصري). الترتيب: الأشد التباساً أولاً.
SIMILAR = {
    "ا": "لد", "ب": "تثن", "ت": "بثن", "ث": "تبن", "ج": "حخ", "ح": "جخ", "خ": "حج", "د": "ذر", "ذ": "دز",
    "ر": "زد", "ز": "رذ", "س": "شص", "ش": "سص", "ص": "ضس", "ض": "صط", "ط": "ظص", "ظ": "طض", "ع": "غح",
    "غ": "عخ", "ف": "قث", "ق": "فن", "ك": "لق", "ل": "اك", "م": "هع", "ن": "بت", "ه": "مع", "و": "رز", "ي": "بن",
}


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _hash(s):
    return hashlib.sha1(_nfc(s).encode("utf-8")).hexdigest()[:10]


def _letter_clusters(word):
    return [c for c in L.clusters(word) if c["kind"] == "letter"]


def _highlight(word, target):
    return [i for i, c in enumerate(_letter_clusters(word)) if L.matches_target(c["ch"], target)]


def _status(ledger, kind, text):
    return ledger.status(kind, text) if ledger else "unreviewed"


# ---------------------------------------------------------------- اختيار الأمثلة
def _blocked(ledger, kind, text):
    return _status(ledger, kind, text) in ("rejected", "needs_change")


def select_examples(letter, position, n, ledger=None, exclude=(), allow_shadda=True):
    """يعيد (قائمة أمثلة، تحذيرات). كل مثال اجتاز check_example بلا أخطاء؛ المرفوض أو المطلوب تعديله بشرياً مستبعد،
    والكلمات المشددة مستبعدة إن كان allow_shadda=False."""
    picked, warns, scored = [], [], []
    for e in words_for(letter, position):
        if _nfc(e["word"]) in {_nfc(x) for x in exclude}:
            continue
        if _blocked(ledger, "word", e["word"]):
            continue
        if not allow_shadda and has_shadda(e["word"]):
            continue
        rep = check_example(e["word"], letter, position)
        if not rep.ok:
            continue
        codes = set(rep.codes())
        score = (0 if "multiple_occurrences" in codes else 4) + (2 if e["illustrable"] else 0) \
            + (1 if "lam_alif_ligature" not in codes else -2) + (3 if _status(ledger, "word", e["word"]) == "approved" else 0) \
            - len(rep.letters) * 0.1
        scored.append((score, e, rep))
    scored.sort(key=lambda x: -x[0])
    for _s, e, rep in scored[:n]:
        occ = rep.occurrences
        form = _form_of(e["word"], occ[0]["index"]) if occ else "isolated"
        picked.append({**e, "highlight": _highlight(e["word"], letter), "form": form,
                       "position": position, "review_status": _status(ledger, "word", e["word"]),
                       "flags": sorted(codes_of(rep, ("alif_variant", "lam_alif_ligature", "multiple_occurrences")))})
    if len(picked) < min(n, 2):
        warns.append({"code": "insufficient_examples", "position": position, "found": len(picked),
                      "message_ar": f"أمثلة غير كافية للموضع ({L.POSITION_AR_PLAIN[position]}): وُجد {len(picked)}",
                      "message_en": f"only {len(picked)} validated example(s) for position {position}"})
    return picked, warns


def codes_of(rep, wanted):
    return {c for c in rep.codes() if c in wanted}


def _form_of(word, letter_index):
    chars = [x["ch"] for x in _letter_clusters(word)]
    return L.contextual_forms(chars)[letter_index]


# ---------------------------------------------------------------- بناء الوحدات
class _B:
    """مُجمِّع وحدات مع ترقيم ثابت داخل كل مرحلة."""

    def __init__(self, lang, age, reps=1, profile=None):
        self.lang, self.age, self.reps, self.units, self._n = lang, age, reps, [], {}
        self.p = profile or PROFILES["standard"]

    def add(self, stage, utype, text, *, repeat=False, delivery="natural", display=None, picture=None,
            title=None, extra_pause=0.0, group=None):
        self._n[stage] = self._n.get(stage, 0) + 1
        speech = round(SE.speech_seconds(text, self.age, delivery, self.lang) * self.p["speech_factor"], 2)
        base = self.p["repeat_pause"] if self.p["repeat_pause"] is not None else SE.repeat_pause(speech, self.age)
        pause = (base + self.p["pause_extra"]) * self.reps if repeat else 0.0
        dur = round(max(UNIT_MIN_VISUAL, speech + pause + extra_pause), 2)
        u = {"id": f"{stage}{self._n[stage]:02d}", "stage": stage, "type": utype, "text": text,
             "text_hash": _hash(text), "delivery": delivery, "repeat": repeat, "repeat_count": self.reps if repeat else 0,
             "speech_seconds": speech, "pause_seconds": round(pause + extra_pause, 2), "duration_seconds": dur,
             "display": display or {}}
        if title:
            u["title"] = title
        if picture:
            u["picture"] = picture
        if group:
            u["group"] = group
        self.units.append(u)
        return u


def _join_key(letter, form, position):
    j = L.JOINING[letter]
    if j == "dual":
        if form == "medial":
            return "join_both"
        if form == "final":
            return "join_prev_only"
        if form == "initial" and position != "initial":
            return "join_isolated_after_right"
        return "join_next_only"
    if j == "right":
        return "join_prev_only" if form == "final" else "join_no_next"
    return "join_no_next"


def _name(letter):
    return L.LETTERS[letter]["name"]


def build_letter_lesson(letter, *, age_band="child", lang="ar", target_seconds=None, taught=(), ledger=None,
                        examples_per_position=None, reps=1, tolerance=0.10, with_sukun=True, with_sentence=True,
                        quiz_items=None, profile="standard"):
    """يبني درس حرف كاملاً. إن حُدّد target_seconds يُضبط عدد الأمثلة والتكرار ليقع الإجمالي ضمن السماحية
    قدر الإمكان، ويُرجَع duration_report صادق (within_tolerance قد يكون False)."""
    if letter not in L.LETTERS:
        raise ValueError(f"not an Arabic base letter: {letter!r}")
    if lang not in ("ar", "en"):
        raise ValueError("lang must be 'ar' or 'en'")
    if age_band not in SE.WPS:
        raise ValueError(f"age_band must be one of {sorted(SE.WPS)}")
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {sorted(PROFILES)}")
    prof = PROFILES[profile]
    if target_seconds is None:
        target_seconds = prof["default_target"]
    if quiz_items is None:
        quiz_items = prof["quiz_items"]

    if examples_per_position is not None or target_seconds is None:
        combos = [(examples_per_position or prof["examples"], reps)]
    else:
        combos = [(n, r) for n in prof["combos_n"] for r in prof["combos_r"]]
    best = None
    for n, r in combos:
        lesson = _assemble(letter, age_band, lang, taught, ledger, n, r, with_sukun, with_sentence, quiz_items, profile)
        total = lesson["duration_report"]["total_seconds"]
        if target_seconds is None:
            best = lesson
            break
        dev = abs(total - target_seconds)
        if best is None or dev < best[0]:
            best = (dev, lesson)
        if SE.fit_report(total, target_seconds, tolerance)["within_tolerance"]:
            best = (dev, lesson)
            break
    lesson = best if target_seconds is None else best[1]
    if target_seconds is not None:
        rep = SE.fit_report(lesson["duration_report"]["total_seconds"], target_seconds, tolerance)
        lesson["duration_report"].update(rep)
        if not rep["within_tolerance"]:
            lesson["warnings"].append({
                "code": "duration_out_of_tolerance",
                "message_ar": f"المدة {rep['total_seconds']}ث خارج {int(tolerance * 100)}% من الهدف {target_seconds}ث؛ "
                              "عدّل الهدف أو أضف/احذف مراحل",
                "message_en": f"duration {rep['total_seconds']}s outside ±{int(tolerance * 100)}% of target {target_seconds}s"})
    return lesson


def _assemble(letter, age, lang, taught, ledger, n_ex, reps, with_sukun, with_sentence, quiz_items, profile="standard"):
    prof = PROFILES[profile]
    info = L.LETTERS[letter]
    nm = _name(letter)
    nm_en = LETTER_NAME_EN.get(letter, info["name_plain"])
    warnings, review, examples = [], [], {}

    def T(key, **kw):
        return t(lang, key, name=nm, name_en=nm_en, **kw)

    b = _B(lang, age, reps, prof)
    forms = L.letter_forms_display(letter)
    syl = L.syllables(letter)

    # ---- A: تعرّف (مستويات 1–2)
    b.add("A", "intro", T("welcome"), display={"letter": letter})
    b.add("A", "letter_card", T("this_is"), display={"letter": letter, "name": nm})
    b.add("A", "forms", T("forms_dual" if info["joining"] == "dual" else "forms_right"),
          display={"letter": letter, "forms": {k: v for k, v in forms.items() if v}}, extra_pause=1.0)
    key = {"ا": "sound_alif", "و": "sound_waw", "ي": "sound_yaa"}.get(letter, "name_vs_sound")
    b.add("A", "sound", T(key, syl=syl[0]["text"]), repeat=True, display={"letter": letter, "syllable": syl[0]["text"]})
    if prof["repeat_cue"]:       # في preschool الترديد مدمج في كل وحدة، فلا داعي لوحدة منفصلة
        b.add("A", "repeat", T("repeat_me"), repeat=True, display={"letter": letter}, group="cue")

    # ---- B/C/D: أمثلة بحسب الموضع (مستوى 3)
    for pos in ("initial", "medial", "final"):
        stg = POS_KEY[pos]
        exs, w = select_examples(letter, pos, n_ex, ledger, allow_shadda=prof["allow_shadda"])
        warnings += w
        examples[pos] = exs
        if not exs:
            continue
        b.add(stg, "position_intro", T(f"intro_{pos}"), display={"letter": letter, "position": pos})
        for k, e in enumerate(exs):
            pic = {"concept_en": e["concept_en"], "category": e["category"], "illustrable": e["illustrable"]}
            if not e["illustrable"]:
                warnings.append({"code": "not_illustrable", "word": e["word"],
                                 "message_ar": f"«{e['word']}» مفهوم يصعب تصويره", "message_en": f"{e['word']} is hard to illustrate"})
            wkey = "word_say_with_me" if prof["call_response"] else f"word_{pos}"
            b.add(stg, "word", T(wkey, word=e["word"]), repeat=True, picture=pic,
                  display={"word": e["word"], "letter": letter, "letter_highlight": e["highlight"], "position": pos,
                           "form": e["form"]})
            if prof["join_once"] and k > 0 and e["form"] == exs[0]["form"]:
                continue
            b.add(stg, "connection", T(_join_key(letter, e["form"], pos)),
                  display={"word": e["word"], "letter": letter, "letter_highlight": e["highlight"], "form": e["form"]})
    if letter == "ا":
        b.add("D", "contrast", T("alif_maksura"),
              display={"alif": "ا", "maksura": "ى", "examples": [c["word"] for c in MAKSURA_CONTRAST[:2]]},
              extra_pause=2.0)
        examples["maksura_contrast"] = MAKSURA_CONTRAST[:2]
        for c in MAKSURA_CONTRAST[:2]:
            review.append({"kind": "word", "text": c["word"], "reason": "alif_maksura_contrast",
                           "status": _status(ledger, "word", c["word"])})

    # ---- E: مقاطع بالحركات والمدود (مستويات 4–5)
    b.add("E", "syllables_intro", T("intro_syllables"), display={"letter": letter})
    for s in syl:
        if prof["syllable_marks"] and s["mark"] not in prof["syllable_marks"]:
            continue
        b.add("E", "syllable", T(f"syl_{s['mark']}" if s["mark"] in ("fatha", "kasra", "damma") else f"syl_{s['mark']}", syl=s["text"]),
              repeat=True, delivery="slow", display={"syllable": s["text"], "letter": letter, "ipa": s["ipa"]})
    if with_sukun and prof["sukun"]:
        sk = _find_sukun_word(letter, ledger, prof["allow_shadda"])
        if sk:
            b.add("E", "sukun", T("sukun", word=sk["word"]), delivery="slow", repeat=True,
                  picture={"concept_en": sk["concept_en"], "category": sk["category"], "illustrable": sk["illustrable"]},
                  display={"word": sk["word"], "letter": letter, "letter_highlight": sk["highlight"]})
            examples["sukun"] = sk

    # ---- F: قراءة (مستويات 6–7)
    allowed = set(taught) | {letter}
    readable = _readable_words(letter, allowed, examples, n_ex, prof["allow_shadda"])
    if not readable:
        warnings.append({"code": "no_readable_words_with_taught_letters",
                         "message_ar": "لا توجد كلمات مكوّنة من الحروف المُدرَّسة فقط؛ استُخدمت كلمات الدرس",
                         "message_en": "no words made only of taught letters; fell back to lesson words"})
        readable = [e for pos in ("initial", "medial", "final") for e in examples.get(pos, [])][:prof["read_words"]]
    if readable:
        b.add("F", "reading_intro", T("intro_reading"), display={"letter": letter})
        for e in readable[:prof["read_words"]]:
            sylls = _syllable_split(e["word"])
            disp = {"word": e["word"], "letter": letter, "letter_highlight": e.get("highlight", _highlight(e["word"], letter)),
                    "syllables": sylls}
            b.add("F", "read", T("read_slow"), delivery="slow", display=disp, extra_pause=1.0 + 0.8 * len(sylls))
            b.add("F", "read", T("read_natural"), display=disp, repeat=True)

    # ---- G: جملة (مستوى 8)
    sentence = None
    if with_sentence:
        prefer = [e["word"] for pos in ("initial", "medial", "final") for e in examples.get(pos, [])]
        sentence = build_sentence(letter, prefer_words=prefer)
        if sentence and not prof["allow_shadda"] and has_shadda(sentence["text"]):
            warnings.append({"code": "sentence_has_shadda", "message_ar": "الجملة فيها شدة (غالباً لام شمسية)؛ تُسمَع ولا تُقطَّع",
                             "message_en": "sentence contains shadda (often sun-letter lam); listen-only"})
        if sentence:
            chk = check_sentence(sentence["text"])
            if not chk["ok"]:
                warnings.append({"code": "sentence_failed_validation", "message_ar": "فشل فحص الجملة المولَّدة",
                                 "message_en": "generated sentence failed validation", "issues": chk["issues"]})
                sentence = None
        if sentence:
            b.add("G", "sentence_intro", T("intro_sentence"), display={"letter": letter})
            b.add("G", "sentence", sentence["text"], delivery="slow" if age == "child" else "natural", repeat=True,
                  display={"sentence": sentence["text"], "tokens": sentence["tokens"], "highlights": sentence["highlights"],
                           "letter": letter, "translation_en": sentence["translation_en"]})
            review.append({"kind": "sentence", "text": sentence["text"], "reason": "template_sentence_meaning_and_style",
                           "status": _status(ledger, "sentence", sentence["text"])})
        else:
            warnings.append({"code": "no_sentence", "message_ar": "لم تُولَّد جملة لهذا الحرف",
                             "message_en": "no sentence generated for this letter"})

    # ---- H: اختبار
    quiz = _build_quiz(letter, examples, taught, quiz_items, allow_shadda=prof["allow_shadda"])
    if quiz:
        b.add("H", "quiz_intro", T("quiz_intro"), display={"letter": letter})
        for q in quiz:
            qtext = {"which_starts_with": lambda: T("q_initial"), "where_in_word": lambda: T("q_where", word=q["word"]),
                     "sound_choice": lambda: T("q_sound", syl=q["answer"]),
                     "find_letter": lambda: T("q_find_letter")}[q["kind"]]()
            b.add("H", "quiz", qtext, extra_pause=4.0, display={"quiz_id": q["id"], "options": q["options"], "letter": letter,
                                                                  "word": q.get("word")})
            ans = q["answer_text"]
            b.add("H", "answer", T("answer_is", answer=ans), display={"quiz_id": q["id"], "correct": q["answer"]})
    b.add("H", "closing", T("closing"), display={"letter": letter})

    # ---- مراجعة بشرية
    review.insert(0, {"kind": "letter", "text": letter, "reason": "pronunciation_and_name",
                      "status": _status(ledger, "letter", letter),
                      "detail": info["sound_note"] or "تأكيد نطق الحرف واسمه"})
    if letter in HARD_SOUNDS:
        review[0]["reason"] = "pronunciation_hard_sound"
    seen = set()
    for pos in ("initial", "medial", "final"):
        for e in examples.get(pos, []):
            if e["word"] in seen:
                continue
            seen.add(e["word"])
            if e["review_status"] != "approved":
                review.append({"kind": "word", "text": e["word"], "reason": "unreviewed_word", "status": e["review_status"],
                               "flags": e["flags"]})
    if letter == "ا":
        review.append({"kind": "note", "text": "ا / أ / إ / آ / ى", "reason": "alif_variants_taught_to_child",
                       "status": "unreviewed"})

    stages = sorted({u["stage"] for u in b.units})
    prog = assert_progression("".join(stages))
    total = round(sum(u["duration_seconds"] for u in b.units), 2)
    by_stage = {s: round(sum(u["duration_seconds"] for u in b.units if u["stage"] == s), 2) for s in stages}

    pending = [r for r in review if r["status"] != "approved"]
    return {
        "schema_version": SCHEMA_VERSION, "kind": "letter_lesson", "letter": letter, "name": nm, "name_en": nm_en,
        "lang": lang, "age_band": age, "joining": info["joining"], "forms": {k: v for k, v in forms.items() if v},
        "stages": [{"stage": s, "title_ar": STAGE_TITLES[s], "levels": STAGE_LEVELS[s]} for s in stages],
        "progression_issues": prog,
        "profile": profile,
        "params": {"examples_per_position": n_ex, "repetitions": reps, "taught": list(taught), "profile": profile},
        "units": b.units, "examples": examples, "sentence": sentence, "quiz": quiz,
        "review": {"needs_human_review": pending, "all_approved": not pending},
        "duration_report": {"total_seconds": total, "by_stage": by_stage, "unit_count": len(b.units)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------- مساعدات
def _find_sukun_word(letter, ledger, allow_shadda=True):
    for e in words_for(letter):
        if _blocked(ledger, "word", e["word"]) or (not allow_shadda and has_shadda(e["word"])):
            continue
        cl = _letter_clusters(e["word"])
        for i, c in enumerate(cl):
            if L.matches_target(c["ch"], letter) and L.SUKUN in c["marks"] and check_example(e["word"], letter).ok:
                return {**e, "highlight": [i], "review_status": _status(ledger, "word", e["word"])}
    return None


def _readable_words(letter, allowed, examples, n, allow_shadda=True):
    out = []
    pool = [e for pos in ("initial", "medial", "final") for e in examples.get(pos, [])] + words_for(letter)
    seen = set()
    for e in pool:
        w = e["word"]
        if w in seen or (not allow_shadda and has_shadda(w)):
            continue
        seen.add(w)
        chars = {c["ch"] for c in _letter_clusters(w)}
        norm = {("ا" if ch in L.ALIF_FAMILY else ch) for ch in chars}
        if norm <= allowed | {"ة"} and (allowed == {letter} or len(chars) > 1) and check_example(w, letter).ok:
            out.append({**e, "highlight": _highlight(w, letter)})
    out.sort(key=lambda e: len(e["word"]))
    return out


def _syllable_split(word):
    return syllable_texts(word)


POS_ANSWER_AR = {"initial": "فِي الْأَوَّلِ", "medial": "فِي الْوَسَطِ", "final": "فِي الْآخِرِ"}


def _rot(items, seed):
    """ترتيب حتمي يختلف من حرف لآخر، كي لا يكون موضع الإجابة الصحيحة ثابتاً."""
    return sorted(items, key=lambda x: _hash(f"{x}|{seed}"))


def _build_quiz(letter, examples, taught, k, allow_shadda=True):
    """تمارين متنوعة: أي كلمة تبدأ بالحرف، أين الحرف في الكلمة، أي مقطع سمعتم، أي هذه هو الحرف.
    يُضمن ألا تتكرر الإجابة الصحيحة نفسها في سؤالَي «أين الحرف» ما أمكن."""
    by_kind = {kd: [] for kd in QUIZ_KINDS}
    ex_init = examples.get("initial", [])
    others = []
    for l2 in L.LETTER_ORDER:
        if l2 == letter:
            continue
        for e in BANK.get(l2, {}).get("initial", []):
            if not allow_shadda and has_shadda(e["word"]):
                continue
            if not any(L.matches_target(c["ch"], letter) for c in _letter_clusters(e["word"])):
                others.append(e)
    tset = set(taught)
    pref = [e for e in others if tset and all(("ا" if c["ch"] in L.ALIF_FAMILY else c["ch"]) in tset for c in _letter_clusters(e["word"]))]
    pool = pref or others
    if ex_init:
        ans = ex_init[0]
        distractors = _spread(pool, 2, seed=letter)
        opts = _rot([ans["word"]] + [d["word"] for d in distractors], letter)
        by_kind["which_starts_with"].append({"kind": "which_starts_with", "options": opts, "answer": ans["word"],
                                             "answer_text": ans["word"], "letter": letter,
                                             "picture_concepts": [ans["concept_en"]] + [d["concept_en"] for d in distractors]})
    # أين الحرف؟ نتنقل بين المواضع بترتيب يعتمد على الحرف، وكلمة غير مستعملة في سؤال «تبدأ بـ»
    used = {ex_init[0]["word"]} if ex_init else set()
    for pos in _rot(["medial", "final", "initial"], letter + "pos"):
        for e in examples.get(pos, []):
            if "multiple_occurrences" in e["flags"] or e["word"] in used:
                continue
            used.add(e["word"])
            by_kind["where_in_word"].append({"kind": "where_in_word", "word": e["word"],
                                             "options": ["initial", "medial", "final"], "answer": e["position"],
                                             "answer_text": POS_ANSWER_AR[e["position"]], "highlight": e["highlight"]})
            break
    # أي مقطع سمعتم؟ (تمييز سمعي للحركات القصيرة)
    short = [s for s in L.syllables(letter) if s["mark"] in ("fatha", "kasra", "damma")]
    if len(short) == 3:
        target = short[int(_hash(letter + "snd"), 16) % 3]
        by_kind["sound_choice"].append({"kind": "sound_choice", "options": _rot([s["text"] for s in short], letter + "s"),
                                        "answer": target["text"], "answer_text": target["text"], "letter": letter,
                                        "mark": target["mark"]})
    # أي هذه هو الحرف؟ (تمييز بصري بين حروف متشابهة)
    sim = [c for c in SIMILAR.get(letter, "") if c in L.LETTERS][:2]
    if len(sim) == 2:
        by_kind["find_letter"].append({"kind": "find_letter", "options": _rot([letter] + sim, letter + "f"),
                                       "answer": letter, "answer_text": L.LETTERS[letter]["name"], "letter": letter,
                                       "confusables": sim})
    # تجميع: نوع واحد من كل صنف أولاً، ثم سؤال «أين» إضافي إن طُلب أكثر
    quiz = [by_kind[kd][0] for kd in QUIZ_KINDS if by_kind[kd]]
    extra = by_kind["where_in_word"][1:]
    quiz = (quiz + extra)[:k]
    for i, q in enumerate(quiz, start=1):
        q["id"] = f"q{i}"
    return quiz


def _spread(pool, n, seed):
    """اختيار مشتتات حتمي ومتنوعة (حرف أول مختلف)."""
    out, firsts = [], set()
    for e in sorted(pool, key=lambda e: _hash(e["word"] + seed)):
        f = _letter_clusters(e["word"])[0]["ch"]
        if f in firsts:
            continue
        firsts.add(f)
        out.append(e)
        if len(out) == n:
            break
    return out
