"""المخرج الإبداعي: يحوّل ملخص المشروع إلى ملخص إبداعي وخطة إنتاج. الهيكل والتحذيرات حتمية؛
والنصوص الوصفية الأغنى (مفهوم، حبكة) يضيفها المضيف Claude عبر HostTask ثم تُتحقَّق بنفس المخطط."""
from ..core import workflow as W
from ..systems.style_manager.manager import StyleManager

RHYTHM = {"child": (6, 12), "preteen": (8, 16), "teen": (10, 22), "adult": (12, 30)}   # ثوانٍ لكل مشهد (أدنى، أقصى)
NARRATIVE = {
    "kids_education": "تعرّف → أمثلة بحسب الموضع → مقاطع بالحركات → قراءة → جملة → تمرين → ختام (مراحل A–H مع تكرار وتعزيز)",
    "educational": "خطّاف → المفهوم → مثال → الخطأ الشائع وتصحيحه → تدريب → خلاصة",
    "documentary": "افتتاح تأسيسي → سياق → أدلة وشهادات → تفسير → خلاصة وأسئلة مفتوحة",
    "storytelling": "تمهيد → عقدة → تصاعد → حل → عبرة",
    "scientific": "سؤال → فرضية → عرض بصري للآلية → نتائج → حدود المعرفة",
    "motion_graphics": "عنوان → نقاط/بيانات متحركة → إبراز الرقم/الفكرة الرئيسية → خلاصة",
    "social_media": "خطّاف في 3 ثوانٍ → فكرة واحدة → دعوة لإجراء",
    "other": "افتتاح → صلب الموضوع → خلاصة",
}
NARRATION = {"child": "جمل قصيرة مشكولة بنبرة ودودة، تكرار متعمّد، وقفات للترديد", "preteen": "جمل واضحة بأمثلة من حياة الطفل",
             "teen": "شرح مباشر بنبرة محفّزة وأمثلة معاصرة", "adult": "شرح دقيق متوازن بمصطلحات مضبوطة"}
CATEGORY = {"kids_education": "محتوى تعليمي للأطفال", "educational": "محتوى تعليمي", "documentary": "وثائقي", "storytelling": "قصصي",
            "scientific": "علمي", "motion_graphics": "موشن جرافيك", "social_media": "تواصل اجتماعي", "other": "عام"}

CREATIVE_BRIEF_SCHEMA = {"type": "object", "required": ["content_category", "narrative_structure", "visual_identity", "audience_expectations",
                         "storytelling_approach", "scene_rhythm", "color_direction", "character_requirements", "animation_requirements",
                         "narration_style", "visual_style", "production_plan"]}


def direct(project, styles=None):
    styles = styles or StyleManager()
    st = styles.get(project["visual_style"]) if not project["visual_style"].startswith("hybrid:") else None
    if st is None:
        a, b = project["visual_style"][7:].split("+")
        st = styles.get(f"{a}+{b}") if f"{a}+{b}" in styles.all() else styles.combine(a, b)
    age, ptype = project["audience"]["age_band"], project["project_type"]
    lo, hi = RHYTHM[age]
    total = project["duration"]["seconds"]
    warnings = []
    if st["render_support"] == "provider_required":
        warnings.append(f"النمط «{st['name_ar']}» لا يُصيَّر محلياً: سيُنتَج تخطيط ومواصفات فقط حتى يُحدَّد مزوّد صور/فيديو")
    if st["render_support"] == "partial":
        warnings.append(f"النمط «{st['name_ar']}» جزئي محلياً: {st['notes']}")
    if project["format"].get("aspect", "16:9") != "16:9" and "local_engine" in st["compatible_engines"]:
        warnings.append("المحرك المحلي يصيّر 16:9 فقط؛ النسبة المطلوبة تتطلب مزوّداً أو قصّاً لاحقاً")
    if project["narration"]["mode"] == "tts_service":
        warnings.append("لا يوجد مزوّد صوت مدمج؛ استعمل تسجيلاً بشرياً أو حدّد مزوّداً")
    if ptype == "kids_education":
        chars = ["معلم ودود بصوت واضح", "طالبة/طالب يكرّر ويجيب (اختر الجنس واحدّده في بطاقة الشخصية ثم التزم به)"]
    else:
        chars = ["راوٍ أو مقدّم", "شخصيات داعمة عند الحاجة"]
    plan = [{"stage": s.id, "title_ar": s.title_ar, "approval_required": s.approval, "expensive": s.expensive, "owner": s.owner}
            for s in W.STAGES]
    return {"content_category": CATEGORY[ptype], "narrative_structure": NARRATIVE[ptype],
            "visual_identity": f"{st['name_ar']}: {st['visual_instructions']}", "audience_expectations": f"فئة {age}، مستوى {project['audience'].get('level', 'beginner')}",
            "storytelling_approach": "مشاهد قصيرة بهدف واحد لكل مشهد، تكرار وتعزيز" if ptype == "kids_education" else "هدف واحد لكل مشهد مع انتقال منطقي",
            "scene_rhythm": {"min_seconds": lo, "max_seconds": hi, "suggested_scene_count": [round(total / hi), round(total / lo)]},
            "color_direction": st["palette"], "character_requirements": chars,
            "animation_requirements": st["requirements"], "narration_style": NARRATION[age],
            "visual_style": project["visual_style"], "style_render_support": st["render_support"],
            "kids_priorities": ["أهداف تعلّم واضحة", "مفردات بسيطة", "شرح يناسب العمر", "سرد بصري ودود", "تكرار وتعزيز", "مشاهد قصيرة مفهومة"] if ptype == "kids_education" else [],
            "warnings": warnings, "production_plan": plan, "target_seconds": total}
