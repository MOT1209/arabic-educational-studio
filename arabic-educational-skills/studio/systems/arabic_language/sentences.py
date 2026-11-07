"""جُمل الأطفال: توليد من قوالب معجمية + تحقق نحوي حتمي لما أُنتج من القوالب.

القالب المدعوم: فعل ماضٍ + فاعل مرفوع + مفعول به معرَّف بـ«ال» منصوب  (أَكَلَ أَحْمَدُ التُّفَّاحَةَ).
الجمل خارج القالب لا يمكن إثبات نحوها آلياً: تُفحص بنيوياً فقط وتُوسَم unverified_grammar لمراجعة معلم.
"""
import unicodedata

from . import letters as L
from .bank import all_entries
from .orthography import split_sentence, validate_sentence

NFC = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731

VERBS = {  # الماضي للمفرد المذكر الغائب
    "أَكَلَ": {"en": "ate", "objects": {"food"}},
    "شَرِبَ": {"en": "drank", "objects": {"drink"}},
    "حَمَلَ": {"en": "carried", "objects": {"object"}},
    "رَسَمَ": {"en": "drew", "objects": {"animal", "nature", "object"}},
}
SUBJECTS = {  # الفاعل بصيغة الرفع الصحيحة
    "أَحْمَدُ": ("m", "Ahmad"), "عُمَرُ": ("m", "Omar"), "يُوسُفُ": ("m", "Youssef"), "خَالِدٌ": ("m", "Khaled"),
    "سَلْمَى": ("f", "Salma"), "لَيْلَى": ("f", "Layla"), "مَرْيَمُ": ("f", "Maryam"), "فَاطِمَةُ": ("f", "Fatima"),
    "سَارَةُ": ("f", "Sara"), "لُبْنَى": ("f", "Lubna"),
    "الْوَلَدُ": ("m", "the boy"), "الْبِنْتُ": ("f", "the girl"), "الطِّفْلُ": ("m", "the child"),
}
DRINKS = [("لَبَن", "milk"), ("شَاي", "tea"), ("مَاء", "water")]


def _fix_last(cl, fn):
    cl[-1] = dict(cl[-1], marks=fn(list(cl[-1]["marks"])))
    return cl


def feminine_past(verb):
    """الماضي مع فاعل مؤنث غائب: الفعل بفتحته الأخيرة + تاء ساكنة (أَكَلَ ← أَكَلَتْ)."""
    return NFC(verb + "ت" + L.SUKUN)


def definite_accusative(noun):
    """«أَسَد» ← «الْأَسَدَ»، «تُفَّاحَة» ← «التُّفَّاحَةَ» (لام شمسية: شدّة على أول الحرف)."""
    cl = L.clusters(noun)
    first = cl[0]
    sun = first["ch"] in L.SUN_LETTERS
    if sun and L.SHADDA not in first["marks"]:
        cl[0] = dict(first, marks=[L.SHADDA] + first["marks"])
    if cl[-1]["ch"] not in "اى":
        _fix_last(cl, lambda m: [x for x in m if x not in L.VOWEL_LIKE] + [L.FATHA])
    return NFC("ا" + "ل" + ("" if sun else L.SUKUN) + "".join(L.cluster_text(c) for c in cl))


def _objects_for(verb):
    cats = VERBS[verb]["objects"]
    pool, seen = [], set()
    if "drink" in cats:
        pool += [(n, en, "drink") for n, en in DRINKS]
    for e in all_entries():
        if e["category"] in cats and e["illustrable"] and e["word"] not in seen:
            seen.add(e["word"]); pool.append((e["word"], e["concept_en"], e["category"]))
    return pool


def _target_hits(tokens, target, article_tokens):
    hits = []
    for ti, t in enumerate(tokens):
        cl = [c for c in L.clusters(t) if c["kind"] == "letter"]
        skip = 2 if ti in article_tokens else 0
        idx = [i for i, c in enumerate(cl) if i >= skip and L.matches_target(c["ch"], target)]
        if idx:
            hits.append({"token": ti, "cluster_indices": idx})
    return hits


def build_sentence(target, prefer_words=(), max_hits=3):
    """أفضل جملة قالبية تحوي الحرف المستهدف منطوقاً (لا في أداة التعريف). None إن تعذّر."""
    prefer = {NFC(w) for w in prefer_words}
    best = None
    for vi, (verb, vinfo) in enumerate(VERBS.items()):
        for si, (subj, (gender, sen)) in enumerate(SUBJECTS.items()):
            v = verb if gender == "m" else feminine_past(verb)
            for noun, concept, _cat in _objects_for(verb):
                obj = definite_accusative(noun)
                toks = [v, subj, obj]
                hits = _target_hits(toks, target, {2})
                if not hits:
                    continue
                total = sum(len(h["cluster_indices"]) for h in hits)
                score = (3 if NFC(noun) in prefer else 0) + (2 if total <= max_hits else -total) + (1 if any(h["token"] == 2 for h in hits) else 0)
                key = (score, -(vi * 100 + si))
                if best is None or key > best[0]:
                    obj_en = ("the " + concept)
                    best = (key, {"text": " ".join(toks) + ".", "tokens": toks, "highlights": hits, "structure": "VSO",
                                  "translation_en": f"{sen[0].upper() + sen[1:]} {vinfo['en']} {obj_en}.",
                                  "source": "template", "verified_grammar": True})
    return best[1] if best else None


def check_sentence(text, kids=True):
    """يعيد {ok, structure, verified_grammar, issues}. ok=False عند خطأ بنيوي؛ verified_grammar=False = تحتاج معلماً."""
    res = validate_sentence(text, kids=kids)
    issues = [{k: v for k, v in i.items()} for i in res["issues"]]
    toks = res["tokens"]
    verified, structure = False, None
    if len(toks) == 3:
        v, s, o = (NFC(t) for t in toks)
        subj = {NFC(k): g for k, (g, _) in SUBJECTS.items()}
        for verb in VERBS:
            g = subj.get(s)
            if g is None:
                continue
            expect = NFC(verb if g == "m" else feminine_past(verb))
            if v == expect and o in {NFC(definite_accusative(n)) for n, _, _ in _objects_for(verb)}:
                verified, structure = True, "VSO"
                break
            if v == expect:
                issues.append({"code": "object_not_in_lexicon", "severity": "review", "word": toks[2],
                               "message_ar": "المفعول به خارج المعجم المعتمد للفعل (تعذّر إثبات الإعراب أو ملاءمة المعنى)",
                               "message_en": "object not in the verified lexicon for this verb"})
        if not verified and not any(i["code"] == "object_not_in_lexicon" for i in issues):
            issues.append({"code": "agreement_or_case_mismatch_or_unknown", "severity": "review", "word": "",
                           "message_ar": "الجملة لا تطابق القالب المعتمد (مطابقة الفعل للفاعل أو الإعراب أو المفردات)",
                           "message_en": "sentence does not match the verified template (agreement/case/lexicon)"})
    else:
        issues.append({"code": "unverified_grammar", "severity": "review", "word": "",
                       "message_ar": "لا قالب نحوي معتمد لهذه الجملة؛ تحتاج مراجعة معلم",
                       "message_en": "no verified template for this sentence; teacher review required"})
    return {"ok": res["ok"], "structure": structure, "verified_grammar": verified, "issues": issues, "end": res["end"],
            "tokens": toks}
