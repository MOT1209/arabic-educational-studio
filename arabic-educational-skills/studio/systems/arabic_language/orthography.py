"""مدقق إملائي وموضعي حتمي لكلمات وجمل التعليم. لا يستدعي نموذجاً لغوياً.

ما يتحقق منه الكود (حتمي): الحروف المسموحة، ترتيب التشكيل، الألف والألف المقصورة، التاء المربوطة،
موضع الحرف المستهدف وشكله، اتصال الحروف.
ما لا يستطيع الكود إثباته (يُوسَم needs_review): صحة المعنى والفصاحة والنطق، وأن الكلمة موجودة في معجم.
"""
import re
from dataclasses import dataclass, field

from . import letters as L

ERR, WARN, REVIEW = "error", "warning", "review"


@dataclass
class Report:
    word: str
    issues: list = field(default_factory=list)
    letters: list = field(default_factory=list)
    plain: str = ""

    def add(self, code, severity, ar, en, index=None):
        self.issues.append({"code": code, "severity": severity, "message_ar": ar, "message_en": en, "index": index})

    @property
    def errors(self):
        return [i for i in self.issues if i["severity"] == ERR]

    @property
    def ok(self):
        return not self.errors

    def codes(self, severity=None):
        return [i["code"] for i in self.issues if severity in (None, i["severity"])]

    def to_dict(self):
        return {"word": self.word, "plain": self.plain, "ok": self.ok, "issues": self.issues, "letters": self.letters}


def _vowel_marks(c):
    return [m for m in c["marks"] if m in L.VOWEL_LIKE]


def validate_word(word, kids=True):
    """يفحص كلمة واحدة مشكولة. kids=True يصرّم في التشكيل (يُطلب تشكيل كامل تقريباً)."""
    rep = Report(word=word)
    cl = L.clusters(word)
    if not word or not word.strip():
        rep.add("empty", ERR, "كلمة فارغة", "empty word"); return rep
    for i, c in enumerate(cl):
        if c["kind"] == "orphan":
            rep.add("leading_mark", ERR, "علامة تشكيل بلا حرف قبلها", "diacritic without a base letter", i)
        elif c["kind"] == "other":
            ch = c["ch"]
            if ch in L.PERSIAN_LOOKALIKES:
                rep.add("persian_letter", ERR, f"حرف فارسي/أردي بدل العربي ({ch} ← {L.PERSIAN_LOOKALIKES[ch]})",
                        f"Persian/Urdu lookalike {ch!r}, use {L.PERSIAN_LOOKALIKES[ch]!r}", i)
            elif ch == L.TATWEEL:
                rep.add("tatweel", ERR, "تطويل (ـ) داخل الكلمة", "tatweel inside word", i)
            elif ch.isspace():
                rep.add("space_in_word", ERR, "مسافة داخل كلمة واحدة", "whitespace inside a single word", i)
            else:
                rep.add("invalid_char", ERR, f"محرف غير عربي: {ch!r}", f"non-Arabic character {ch!r}", i)
    letters_cl = [c for c in cl if c["kind"] == "letter"]
    chars = [c["ch"] for c in letters_cl]
    n = len(chars)
    if n == 0:
        rep.add("no_letters", ERR, "لا حروف عربية", "no Arabic letters"); return rep
    rep.plain = "".join(chars)
    forms = L.contextual_forms(chars)
    for i, c in enumerate(letters_cl):
        ch, marks, last = c["ch"], c["marks"], i == n - 1
        vm = _vowel_marks(c)
        rep.letters.append({"index": i, "char": ch, "marks": "".join(marks), "position": L.word_position(i, n),
                            "form": forms[i], "joins_prev": forms[i] in ("medial", "final"),
                            "joins_next": forms[i] in ("initial", "medial")})
        if len(vm) > 1:
            rep.add("multiple_vowels", ERR, f"أكثر من حركة على الحرف {ch}", f"more than one vowel mark on {ch}", i)
        if marks.count(L.SHADDA) > 1:
            rep.add("double_shadda", ERR, f"شدة مكررة على {ch}", f"duplicate shadda on {ch}", i)
        if L.SUKUN in marks and (L.SHADDA in marks or len(vm) > 1):
            rep.add("sukun_conflict", ERR, f"سكون مع شدة أو حركة على {ch}", f"sukun combined with shadda/vowel on {ch}", i)
        if L.SHADDA in marks and not (set(vm) - {L.SUKUN}):
            sev = REVIEW if last else ERR
            rep.add("shadda_without_vowel", sev, f"شدة بلا حركة على {ch}" + (" (قد تكون وقفاً)" if last else ""),
                    f"shadda without a vowel on {ch}" + (" (acceptable only as pausal form)" if last else ""), i)
        if set(marks) & L.TANWEEN:
            ok_pos = last or (i == n - 2 and chars[-1] == "ا" and not letters_cl[-1]["marks"])
            if not ok_pos:
                rep.add("tanween_not_final", ERR, f"تنوين في غير آخر الكلمة على {ch}", f"tanween not at word end on {ch}", i)
        if ch == L.TA_MARBUTA and not last:
            rep.add("ta_marbuta_not_final", ERR, "التاء المربوطة لا تكون إلا في آخر الكلمة", "ta marbuta only at word end", i)
        if ch == L.ALIF_MAKSURA and not last:
            rep.add("alif_maksura_not_final", ERR, "الألف المقصورة لا تكون إلا في آخر الكلمة", "alif maksura only at word end", i)
        if ch == "ا" and i > 0 and (set(vm) - L.TANWEEN):  # همزة الوصل في أول الكلمة تحمل الحركة (اُنْظُرُوا)
            rep.add("alif_has_vowel", ERR, "الألف الساكنة لا تحمل حركة؛ إن كانت همزة فاكتبها أ أو إ",
                    "plain alif cannot carry a vowel; use أ or إ for hamza", i)
        if ch in "أإ" and not vm and kids:
            rep.add("hamza_alif_without_vowel", WARN, f"الهمزة {ch} بلا حركة", f"{ch} has no vowel", i)
    if kids:
        missing = _missing_marks(letters_cl)
        if missing:
            rep.add("missing_diacritics", WARN, "حروف بلا تشكيل: " + "، ".join(f"{chars[i]}({i + 1})" for i in missing),
                    "letters without diacritics: " + ", ".join(f"{chars[i]}({i + 1})" for i in missing), missing[0])
    return rep


def _missing_marks(cl):
    """حروف بلا حركة وليست من المواضع المعفاة (مدّ، آخر الكلمة وقفاً، تاء مربوطة، همزة ألف سبقتها فتحة)."""
    out, n = [], len(cl)
    for i, c in enumerate(cl):
        ch, last = c["ch"], i == n - 1
        if _vowel_marks(c) or L.SHADDA in c["marks"] or L.DAGGER_ALIF in c["marks"] or L.MADDAH in c["marks"]:
            continue
        prev = cl[i - 1] if i else None
        pm = set(prev["marks"]) if prev else set()
        if ch == "ا" and (i == 0 or L.FATHA in pm or L.FATHATAN in pm or L.SHADDA in pm and L.FATHA in pm):
            continue
        if ch == "و" and prev and L.DAMMA in pm:
            continue
        if ch == "ي" and prev and L.KASRA in pm:
            continue
        if ch in (L.TA_MARBUTA, L.ALIF_MAKSURA, "آ") or (last and ch != "أ"):
            continue
        nxt = cl[i + 1] if i + 1 < n else None
        if ch == "ا" and i <= 1 and nxt and nxt["ch"] == "ل":      # ألف أداة التعريف (صامتة)
            continue
        if ch == "ل" and i == 1 and cl[0]["ch"] == "ا" and nxt and L.SHADDA in nxt["marks"]:  # لام شمسية مدغمة
            continue
        out.append(i)
    return out


def check_example(word, target, claimed_position=None, kids=True):
    """يتحقق أن «كلمة المثال» تصلح لدرس الحرف target في الموضع المطلوب.
    claimed_position: initial | medial | final | None (أي موضع)."""
    rep = validate_word(word, kids=kids)
    rep.target, rep.claimed = target, claimed_position
    rep.occurrences = []
    if rep.errors and any(i["code"] in ("empty", "no_letters", "invalid_char") for i in rep.errors):
        return rep
    chars = [x["char"] for x in rep.letters]
    occ = [x for x in rep.letters if L.matches_target(x["char"], target)]
    rep.occurrences = occ
    if not occ:
        if target == "ا" and chars and chars[-1] == L.ALIF_MAKSURA:
            rep.add("alif_maksura_not_alif", ERR,
                    "الكلمة تنتهي بألف مقصورة (ى) وهي حرف مكتوب مختلف عن الألف (ا)؛ لا تصلح مثالاً للألف في آخر الكلمة",
                    "word ends with alif maksura (ى), a different written letter from alif (ا); not valid as an alif example")
        else:
            rep.add("target_missing", ERR, f"الحرف {target} غير موجود في الكلمة", f"target letter {target} not in word")
        return rep
    if claimed_position:
        if claimed_position not in {o["position"] for o in occ}:
            actual = "، ".join(sorted({L.POSITION_AR_PLAIN[o["position"]] for o in occ}))
            rep.add("wrong_position", ERR, f"الحرف في {actual} لا في {L.POSITION_AR_PLAIN[claimed_position]}",
                    f"target occurs at {sorted({o['position'] for o in occ})}, not {claimed_position}")
    if len(occ) > 1:
        rep.add("multiple_occurrences", WARN, f"الحرف يتكرر {len(occ)} مرات؛ لوّنها كلها أو اختر كلمة أبسط",
                f"target occurs {len(occ)} times")
    for o in occ:
        if o["char"] in "أإآ":
            rep.add("alif_variant", REVIEW, f"الألف هنا بصورة {o['char']} (مع همزة/مدّ) وليست ا المجردة؛ اشرح ذلك للطفل",
                    f"{o['char']} is a hamzated/madda alif variant", o["index"])
        if target == "ا" and o["char"] == "ا" and o["index"] > 0 and chars[o["index"] - 1] == "ل":
            rep.add("lam_alif_ligature", WARN, "الألف بعد اللام تكوّن لاماً-ألفاً (لا) وتختلف صورتها؛ يُفضَّل مثال آخر",
                    "alif after lam forms the lam-alif ligature; prefer another example", o["index"])
    return rep


# ---------------- الجُمل ----------------
_PUNCT = ".،,؟?!؛;:"
_SYMBOLS = "≠=+-–—()[]«»\"'…"
_SENT_SPLIT = re.compile(r"\s+")


def split_sentence(text):
    """يقسّم على المسافات، يزيل الترقيم من طرفي كل كلمة، ويُسقط الرموز المنفردة (≠ …).
    `end` = علامة نهاية الجملة الأخيرة إن وُجدت."""
    toks, end = [], ""
    for raw in _SENT_SPLIT.split(text.strip()):
        if not raw:
            continue
        core = raw.strip(_PUNCT + _SYMBOLS)
        trail = raw[len(raw.rstrip(_PUNCT)):] if raw.rstrip(_PUNCT) != raw else ""
        if core:
            toks.append(core)
            end = trail[-1] if trail else ""
        elif raw[-1] in _PUNCT:
            end = raw[-1]
    return toks, end


def validate_sentence(text, kids=True):
    """فحص بنيوي لكل كلمة (لا تحقق نحوي). للنحو انظر sentences.check_sentence."""
    toks, end = split_sentence(text)
    reports = [validate_word(t, kids=kids) for t in toks]
    issues = [dict(i, word=r.word) for r in reports for i in r.issues]
    if not toks:
        issues.append({"code": "empty", "severity": ERR, "message_ar": "جملة فارغة", "message_en": "empty sentence", "word": ""})
    return {"tokens": toks, "end": end, "reports": reports, "issues": issues,
            "ok": not any(i["severity"] == ERR for i in issues)}
