"""التدرج التعليمي (10 مستويات) وربطه بمراحل الدرس."""

LEVELS = [
    (1, "letter_recognition", "التعرّف على الحرف", "يتعرّف الطفل على شكل الحرف واسمه"),
    (2, "letter_sounds", "أصوات الحروف", "ينطق الطفل صوت الحرف ويميّزه عن اسمه"),
    (3, "shapes_positions", "أشكال الحروف ومواضعها", "يميّز الحرف أول الكلمة ووسطها وآخرها ويعرف اتصاله"),
    (4, "short_vowels", "الحركات القصيرة", "يقرأ الحرف مع الفتحة والكسرة والضمة والسكون"),
    (5, "syllables", "المقاطع", "يقرأ مقاطع قصيرة وطويلة (مدّ)"),
    (6, "simple_words", "كلمات بسيطة", "يقرأ كلمات من 2–3 حروف"),
    (7, "longer_words", "كلمات أطول", "يقرأ كلمات من 4 حروف فأكثر"),
    (8, "simple_sentences", "جمل بسيطة", "يقرأ جملة فعلية بسيطة"),
    (9, "reading_comprehension", "فهم المقروء", "يجيب عن أسئلة بعد قراءة جملتين أو ثلاث"),
    (10, "short_stories", "قصص قصيرة وتمارين", "يقرأ قصة قصيرة ويحلّ تمارين"),
]
LEVEL_BY_ID = {l[0]: {"id": l[0], "key": l[1], "title_ar": l[2], "can_do_ar": l[3]} for l in LEVELS}

# كل مرحلة في درس الحرف تقابل مستوى (أو أكثر) من التدرج
STAGE_LEVELS = {"A": [1, 2], "B": [3], "C": [3], "D": [3], "E": [4, 5], "F": [6, 7], "G": [8], "H": []}
STAGE_TITLES = {"A": "التعرّف على الحرف", "B": "الحرف أول الكلمة", "C": "الحرف وسط الكلمة", "D": "الحرف آخر الكلمة",
                "E": "المقاطع والحركات", "F": "الكلمات والقراءة", "G": "الجملة", "H": "التمرين"}

# أي مستويات تتطلب أي سن: لا تُقدَّم مرحلة لفئة أصغر من حدّها
MIN_AGE_FOR_LEVEL = {"child": 8, "preteen": 10, "teen": 10, "adult": 10}


def assert_progression(stages_present):
    """يتأكد أن المستويات المقدَّمة متسلسلة (لا مستوى متقدم بلا أساسه). يعيد قائمة مشاكل."""
    levels = sorted({lv for s in stages_present for lv in STAGE_LEVELS.get(s, [])})
    problems = []
    if levels and levels[0] != 1 and "A" not in stages_present:
        problems.append("الدرس يبدأ بمستوى متقدم دون مرحلة التعرّف (A)")
    gaps = [lv for lv in range(levels[0], levels[-1] + 1) if lv not in levels] if levels else []
    if gaps:
        problems.append(f"فجوة في التدرج: المستويات {gaps} غير مغطّاة بين {levels[0]} و{levels[-1]}")
    return problems
