"""نظام الأسئلة: يقول المستخدم «درس اليوم عن الخبر» فتسأله المهارة أسئلة الأسلوب (لا تسأل إلا ما لا يُستنتج).
questions_for(topic) -> قائمة أسئلة مرتَّبة؛ build_request(topic, answers) -> إعدادات جاهزة للمولّدات.
المهارة تطرح الأسئلة عبر AskUserQuestion (حتى 4 في الدفعة)؛ الافتراضي أول خيار."""
from ..lesson_plan.plan import FONTS, THEMES

LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

Q_STYLE = {"key": "style", "q": "ما أسلوب الفيديو؟", "options": [
    ("teacher", "المعلّم يشرح (شخصية الأستاذ)"), ("song", "الحرف يغنّي «أنا الحرف…» (للحروف فقط)"),
    ("story", "قصة قصيرة تشرح الفكرة"), ("qa", "سؤال وجواب تفاعلي"), ("trace", "تتبّع كتابة الحرف (للحروف فقط)")]}
Q_AUDIO = {"key": "audio", "q": "الصوت؟", "options": [
    ("vocals_only", "أصوات بشرية فقط بلا آلات (موصى به)"), ("with_rhythm", "مع إيقاع خفيف"), ("both", "النسختان")]}
Q_FORMAT = {"key": "format", "q": "شكل الفيديو؟", "options": [
    ("9:16", "Short عمودي"), ("16:9", "أفقي"), ("both", "الاثنان")]}
Q_AGE = {"key": "age", "q": "عمر الجمهور؟", "options": [("preschool", "3–6 سنوات"), ("child", "7–11 سنة"), ("teen", "12+")]}
Q_FONT = {"key": "font", "q": "الخط؟", "options": [
    ("playpen", "Playpen — يدوي طفولي"), ("scheherazade", "Scheherazade — تشكيل واضح"), ("noto_sans", "Noto Sans — نظيف"), ("lemonada", "Lemonada — مرِح")]}
Q_THEME = {"key": "theme", "q": "السمة؟", "options": [(t, t) for t in THEMES[:4]]}
Q_POS = {"key": "position", "q": "كلمات الأنشودة تبدأ بالحرف أم يقع في الوسط/الآخر؟", "options": [
    ("initial", "في أول الكلمة"), ("mixed", "أول ووسط وآخر")]}


def is_letter(topic):
    t = topic.replace("حرف", "").strip()
    return len(t) == 1 and t in LETTERS


def questions_for(topic, known=None):
    known = known or {}
    qs = [Q_STYLE]
    if known.get("style") == "song" or (not known.get("style") and is_letter(topic)):
        qs += [Q_AUDIO]
    qs += [Q_FORMAT, Q_AGE, Q_FONT]
    return [q for q in qs if q["key"] not in known]


def build_request(topic, answers):
    a = {"style": "teacher", "audio": "vocals_only", "format": "9:16", "age": "preschool", "font": "playpen", **answers}
    if a["style"] in ("song", "trace") and not is_letter(topic):
        raise ValueError("أسلوب «أغنية/تتبّع» للحروف فقط؛ اختر أسلوباً آخر لهذا الموضوع")
    if a["font"] not in FONTS:
        raise ValueError(f"خط غير معروف: {a['font']}")
    fmts = ["9:16", "16:9"] if a["format"] == "both" else [a["format"]]
    variants = ["with_rhythm", "vocals_only"] if a["audio"] == "both" else [a["audio"]]
    return {"topic": topic, "style": a["style"], "formats": fmts, "variants": variants, "age_band": a["age"], "font": a["font"],
            "generator": "kids_song.letter_song" if a["style"] == "song" else "kids_learning" if is_letter(topic) else "custom_plan"}
