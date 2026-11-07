"""تقسيم الكلمة المشكولة إلى مقاطع (للتلوين والقراءة البطيئة). يُراجَع بشرياً مع النطق.

الحرف المشدَّد = حرفان: الأول ساكن يُغلق المقطع السابق، والثاني متحرك يفتح المقطع التالي
(بَطَّة = بَطْ | طَة، قُبَّعَة = قُبْ | بَ | عَة). لذلك قد يظهر فهرس الحرف المشدد في مجموعتين.
"""
from . import letters as L


def has_shadda(word):
    return L.SHADDA in word


def _units(word):
    """يعيد قائمة (فهرس الحرف، دوره) حيث الدور: 'plain' أو 'gem_close' (النصف الساكن) أو 'gem_open'."""
    cl = [c for c in L.clusters(word) if c["kind"] == "letter"]
    return cl


def syllabify(word):
    """يعيد قائمة مجموعات؛ كل مجموعة قائمة فهارس حروف (بحسب ترتيب الحروف المكتوبة).
    الحرف المشدد المتحرك يظهر فهرسه مرتين: آخر المقطع السابق وأول المقطع التالي."""
    return [[i for i, _role in g] for g in _syllabify_roles(word)]


def _syllabify_roles(word):
    cl = _units(word)
    groups = []
    mad_of = {"ا": L.FATHA, "و": L.DAMMA, "ي": L.KASRA}
    for i, c in enumerate(cl):
        marks = set(c["marks"])
        has_vowel = bool(marks & (L.SHORT_VOWELS | L.TANWEEN))
        prev_marks = set(cl[i - 1]["marks"]) if i else set()
        if groups and c["ch"] in mad_of and not has_vowel and L.SHADDA not in marks and L.SUKUN not in marks \
                and (mad_of[c["ch"]] in prev_marks or (c["ch"] == "ا" and L.FATHATAN in prev_marks)):
            groups[-1].append((i, "plain"))                     # حرف مدّ
        elif L.SHADDA in marks and not has_vowel and groups:
            groups[-1].append((i, "plain"))                     # شدة في آخر الكلمة عند الوقف (أُمّ): تبقى كما هي
        elif L.SHADDA in marks:
            if groups:
                groups[-1].append((i, "gem_close"))             # النصف الساكن يُغلق المقطع السابق
            if has_vowel or not groups:
                groups.append([(i, "gem_open")])                # النصف المتحرك يفتح مقطعاً جديداً
        elif has_vowel or not groups:
            groups.append([(i, "plain")])
        else:
            groups[-1].append((i, "plain"))                     # سكون أو حرف بلا حركة (وقف) = ختام المقطع السابق
    return groups


def syllable_texts(word):
    """نصوص المقاطع جاهزة للعرض: النصف الساكن يُكتب بسكون، والنصف المتحرك بحركته دون شدة."""
    cl = _units(word)
    out = []
    for g in _syllabify_roles(word):
        parts = []
        for i, role in g:
            c = cl[i]
            if role == "gem_close":
                parts.append(c["ch"] + L.SUKUN)
            elif role == "gem_open":
                vowels = "".join(m for m in c["marks"] if m != L.SHADDA)
                parts.append(c["ch"] + vowels)
            else:
                parts.append(L.cluster_text(c))
        out.append("".join(parts))
    return out
