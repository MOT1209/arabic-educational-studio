"""تعريف المراحل الاثنتي عشرة وقواعد الاعتماد. هذا الملف هو مصدر الحقيقة الوحيد لترتيب العمل."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    id: str
    title_ar: str
    title_en: str
    approval: bool = False       # يتوقف حتى يوافق إنسان
    expensive: bool = False      # يحرّر إنفاقاً/توليداً خارجياً
    schema: str = ""             # مخطط التحقق لمخرجات المرحلة (اختياري)
    owner: str = "host"          # host = Claude المضيف ينفّذ المهمة الإبداعية؛ code = حتمي؛ human = إنسان


STAGES = [   # الترتيب والأسماء مطابقة لقسم «APPROVAL-BASED WORKFLOW» في المواصفة (12 مرحلة)
    Stage("interview", "المقابلة", "Interview", schema="project.schema.json", owner="host"),
    Stage("creative_brief", "الملخص الإبداعي (التوجيه الإبداعي)", "Creative brief / direction", approval=True),
    Stage("research", "البحث", "Research", approval=True),
    Stage("script", "السيناريو", "Script", approval=True, schema="master-script.schema.json"),
    Stage("storyboard", "اللوحة القصصية", "Storyboard", approval=True, schema="storyboard.schema.json"),
    Stage("asset_planning", "تخطيط الأصول والتكلفة (اعتماد الإنفاق)", "Asset planning & cost authorisation",
          approval=True, expensive=True, owner="code"),
    Stage("visual_production", "الإنتاج المرئي", "Visual production", expensive=True, owner="code"),
    Stage("voice_sound", "الصوت والمؤثرات", "Voice & sound production", expensive=True, owner="code"),
    Stage("editing", "المونتاج", "Editing", owner="code"),
    Stage("subtitles", "الترجمة المكتوبة", "Subtitles", owner="code"),
    Stage("qa", "ضبط الجودة", "Quality assurance", owner="code"),
    Stage("final_export", "التصدير النهائي (اعتماد الفيديو)", "Final export (video approval)", approval=True, owner="human"),
]
ORDER = [s.id for s in STAGES]
BY_ID = {s.id: s for s in STAGES}
PASSING = {"approved", "done"}          # حالات تسمح بالمتابعة للمرحلة التالية
STATUSES = {"pending", "awaiting_output", "awaiting_approval", "approved", "done", "rejected", "needs_modification",
            "needs_regeneration", "invalidated", "failed"}


def index(stage_id):
    if stage_id not in BY_ID:
        raise KeyError(f"unknown stage {stage_id!r}; valid: {ORDER}")
    return ORDER.index(stage_id)


def upstream(stage_id):
    return ORDER[:index(stage_id)]


def downstream(stage_id):
    return ORDER[index(stage_id) + 1:]
