"""بيانات الحروف العربية وقواعد الاتصال والأشكال (حتمية، بلا نموذج لغوي).

المصطلحات:
- الموضع في الكلمة (word position): أول/وسط/آخر الكلمة بحسب ترتيب الحروف المكتوبة.
- شكل الحرف (form): معزول/أولي/وسطي/نهائي بحسب الاتصال بالجيران (قد يختلف عن الموضع:
  الألف في وسط «باب» موضعها وسط الكلمة وشكلها نهائي لأنها تتصل بما قبلها فقط).
"""
import unicodedata

# ---- علامات التشكيل (بالرموز الصريحة لتفادي المحارف غير المرئية) ----
FATHATAN, DAMMATAN, KASRATAN = "ً", "ٌ", "ٍ"
FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
SHADDA, SUKUN, DAGGER_ALIF = "ّ", "ْ", "ٰ"
MADDAH, HAMZA_ABOVE, HAMZA_BELOW = "ٓ", "ٔ", "ٕ"
TATWEEL, ZWJ = "ـ", "‍"

SHORT_VOWELS = {FATHA, DAMMA, KASRA}
TANWEEN = {FATHATAN, DAMMATAN, KASRATAN}
VOWEL_LIKE = SHORT_VOWELS | TANWEEN | {SUKUN}          # لا يجتمع منها اثنان على حرف
MARKS = VOWEL_LIKE | {SHADDA, DAGGER_ALIF, MADDAH, HAMZA_ABOVE, HAMZA_BELOW}

MARK_NAMES = {FATHA: "فَتْحَة", DAMMA: "ضَمَّة", KASRA: "كَسْرَة", SUKUN: "سُكُون", SHADDA: "شَدَّة",
              FATHATAN: "تَنْوِين فَتْح", DAMMATAN: "تَنْوِين ضَمّ", KASRATAN: "تَنْوِين كَسْر"}

# ---- الحروف الثمانية والعشرون ----
# joining: dual = يتصل بما قبله وما بعده، right = يتصل بما قبله فقط، none = لا يتصل
_L = {
    "ا": ("أَلِف", "ʔ / aː", "right", "ليس حرفاً صامتاً: صوته مدّ طويل /aː/؛ وحين تحمل همزة (أ إ) يُنطق همزة /ʔ/"),
    "ب": ("بَاء", "b", "dual", ""),
    "ت": ("تَاء", "t", "dual", ""),
    "ث": ("ثَاء", "θ", "dual", "صوت احتكاكي بين الأسنان كأول «think» الإنجليزية"),
    "ج": ("جِيم", "d͡ʒ", "dual", "تختلف لهجياً: /d͡ʒ/ أو /ʒ/ أو /ɡ/؛ الفصحى المعيارية /d͡ʒ/"),
    "ح": ("حَاء", "ħ", "dual", "صوت حلقي احتكاكي لا مقابل له في الإنجليزية"),
    "خ": ("خَاء", "x", "dual", "كالـ «ch» في الألمانية Bach"),
    "د": ("دَال", "d", "right", ""),
    "ذ": ("ذَال", "ð", "right", "كأول «this» الإنجليزية"),
    "ر": ("رَاء", "r", "right", "راء مرفرفة"),
    "ز": ("زَاي", "z", "right", ""),
    "س": ("سِين", "s", "dual", ""),
    "ش": ("شِين", "ʃ", "dual", ""),
    "ص": ("صَاد", "sˤ", "dual", "سين مفخّمة"),
    "ض": ("ضَاد", "dˤ", "dual", "دال مفخّمة"),
    "ط": ("طَاء", "tˤ", "dual", "تاء مفخّمة"),
    "ظ": ("ظَاء", "ðˤ", "dual", "ذال مفخّمة"),
    "ع": ("عَيْن", "ʕ", "dual", "صوت حلقي لا مقابل له في الإنجليزية"),
    "غ": ("غَيْن", "ɣ", "dual", ""),
    "ف": ("فَاء", "f", "dual", ""),
    "ق": ("قَاف", "q", "dual", "تختلف لهجياً (ʔ أو ɡ)؛ الفصحى /q/"),
    "ك": ("كَاف", "k", "dual", ""),
    "ل": ("لَام", "l", "dual", ""),
    "م": ("مِيم", "m", "dual", ""),
    "ن": ("نُون", "n", "dual", ""),
    "ه": ("هَاء", "h", "dual", ""),
    "و": ("وَاو", "w / uː", "right", "حرف صامت /w/ وحرف مدّ /uː/ بعد الضمة"),
    "ي": ("يَاء", "j / iː", "dual", "حرف صامت /j/ وحرف مدّ /iː/ بعد الكسرة"),
}
LETTER_ORDER = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
assert len(LETTER_ORDER) == 28 and set(LETTER_ORDER) == set(_L)

LETTERS = {}
for _c in LETTER_ORDER:
    _name, _ipa, _join, _note = _L[_c]
    LETTERS[_c] = {"char": _c, "name": _name, "name_plain": "".join(x for x in _name if x not in MARKS),
                   "ipa": _ipa, "joining": _join, "sound_note": _note, "index": LETTER_ORDER.index(_c) + 1}

# ---- حروف مركّبة / خاصة تظهر في الكلمات ----
ALIF_FAMILY = set("اأإآٱ")                      # ألف وصورها بالهمزة والمدّ والوصل
ALIF_MAKSURA, TA_MARBUTA, HAMZA = "ى", "ة", "ء"
HAMZA_SEATS = set("ؤئ")
_EXTRA_JOIN = {**{c: "right" for c in "أإآٱؤةى"}, "ئ": "dual", HAMZA: "none"}
JOINING = {**{c: v["joining"] for c, v in LETTERS.items()}, **_EXTRA_JOIN}
WORD_LETTERS = set(JOINING)
PERSIAN_LOOKALIKES = {"ی": "ي", "ک": "ك", "ە": "ه", "ھ": "ه", "ہ": "ه", "ے": "ي"}
SUN_LETTERS = set("تثدذرزسشصضطظنل")

POSITION_AR = {"initial": "أَوَّلُ الْكَلِمَة", "medial": "وَسَطُ الْكَلِمَة", "final": "آخِرُ الْكَلِمَة", "isolated": "مُنْفَرِد"}
POSITION_AR_PLAIN = {"initial": "أول الكلمة", "medial": "وسط الكلمة", "final": "آخر الكلمة", "isolated": "منفرد"}


def is_letter(ch):
    return ch in WORD_LETTERS


def clusters(text):
    """يقسّم النص إلى عناقيد: حرف أساسي + علاماته. المحارف غير العربية عناقيد مستقلة (kind='other')."""
    out = []
    for ch in unicodedata.normalize("NFC", text):
        if ch in MARKS and out and out[-1]["kind"] == "letter":
            out[-1]["marks"].append(ch)
        elif ch in MARKS:
            out.append({"ch": "", "marks": [ch], "kind": "orphan"})
        elif ch in WORD_LETTERS:
            out.append({"ch": ch, "marks": [], "kind": "letter"})
        else:
            out.append({"ch": ch, "marks": [], "kind": "other"})
    return out


def cluster_text(c):
    return c["ch"] + "".join(c["marks"])


def contextual_forms(letters):
    """letters: قائمة محارف أساسية متتالية (كلمة واحدة). يعيد شكل كل حرف."""
    n, forms = len(letters), []
    for i, ch in enumerate(letters):
        jp = i > 0 and JOINING[letters[i - 1]] == "dual" and JOINING[ch] != "none"
        jn = i < n - 1 and JOINING[ch] == "dual" and JOINING[letters[i + 1]] != "none"
        forms.append("medial" if jp and jn else "final" if jp else "initial" if jn else "isolated")
    return forms


def word_position(i, n):
    return "isolated" if n == 1 else "initial" if i == 0 else "final" if i == n - 1 else "medial"


def matches_target(ch, target):
    """ألف تشمل صورها (أ إ آ ٱ) لا الألف المقصورة؛ والباقي تطابق حرفي (ؤ ئ ليست و/ي)."""
    return ch in ALIF_FAMILY if target == "ا" else ch == target


def letter_forms_display(letter):
    """أشكال الحرف الأربعة للعرض (باستخدام وصل الكتابة ZWJ؛ يحتاج خطاً يدعم الاتصال)."""
    j = JOINING[letter]
    return {"isolated": letter,
            "initial": letter + ZWJ if j == "dual" else None,
            "medial": ZWJ + letter + ZWJ if j == "dual" else None,
            "final": ZWJ + letter if j in ("dual", "right") else None}


def syllables(letter):
    """مقاطع الحرف مع الحركات القصيرة والمدود (للمستوى 4–5)."""
    ipa = LETTERS[letter]["ipa"].split(" / ")[0] if letter == "ا" else LETTERS[letter]["ipa"].split(" / ")[0]
    base = "أ" if letter == "ا" else letter
    rows = [{"text": base + FATHA, "ipa": ipa + "a", "mark": "fatha"},
            {"text": ("إ" if letter == "ا" else letter) + KASRA, "ipa": ipa + "i", "mark": "kasra"},
            {"text": base + DAMMA, "ipa": ipa + "u", "mark": "damma"}]
    if letter not in "اوي":
        rows += [{"text": letter + FATHA + "ا", "ipa": ipa + "aː", "mark": "long_a"},
                 {"text": letter + KASRA + "ي", "ipa": ipa + "iː", "mark": "long_i"},
                 {"text": letter + DAMMA + "و", "ipa": ipa + "uː", "mark": "long_u"}]
    return rows
