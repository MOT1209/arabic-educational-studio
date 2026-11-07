"""وكيل المقابلة: سؤال واحد في كل مرة، تكيّفي، لا يعيد سؤالاً أُجيب، يقترح خيارات عند التردد، يقبل افتراضات،
ثم يلخّص الملخص كاملاً ولا يضع approved=True إلا عبر confirm() بعد عرض الملخص. حتمي بلا نموذج لغوي:
المضيف (Claude) يطرح السؤال بصياغته ويمرّر الجواب؛ الكود يحدّد أي سؤال التالي ويتحقق من الجواب ويبني الملخص."""
import json
import re
from pathlib import Path

from ..core.schema import validate_file
from ..systems.arabic_language import letters as _L
from ..systems.style_manager.manager import StyleManager

TYPES = {"kids_education": "تعليم أطفال", "educational": "تعليمي عام", "documentary": "وثائقي", "storytelling": "قصصي",
         "scientific": "علمي", "motion_graphics": "موشن جرافيك", "social_media": "مقاطع تواصل اجتماعي", "other": "آخر"}
AGES = {"child": "طفل (حتى ~9)", "preteen": "ناشئ (10–13)", "teen": "مراهق (14–17)", "adult": "بالغ"}
LEVELS = {"beginner": "مبتدئ", "intermediate": "متوسط", "advanced": "متقدم"}
DURATIONS = {"60": "دقيقة", "120": "دقيقتان", "300": "5 دقائق", "600": "10 دقائق", "custom": "مدة أخرى (حدّدها بالثواني)"}
ASPECTS = {"16:9": "أفقي (يوتيوب)", "9:16": "رأسي (شورتس/ريلز)", "1:1": "مربع", "4:5": "عمودي للمنشورات"}
QUALITY = {"draft": "مسودة سريعة", "standard": "قياسي", "high": "عالٍ"}
NARR = {"human_recording": "تسجيل بشري (مدعوم)", "tts_service": "تحويل نص لصوت (يحتاج مزوّداً غير منفذ حالياً)", "subtitles_only": "ترجمة مكتوبة فقط"}
LANGS = {"ar": "العربية", "en": "الإنجليزية", "ar+en": "ثنائي اللغة"}
WORKFLOWS = {"approval": "مع اعتماد عند كل مرحلة رئيسية", "auto_safe": "آلي للعمليات الآمنة (الاعتمادات الإلزامية تبقى)"}


def _is_kids(a):
    return a.get("project_type") == "kids_education"


def _is_alpha(a):
    return _is_kids(a) and bool(re.search(r"حرف|حروف|أبجدي|ابجدي|alphabet|letter", a.get("topic", ""), re.I))


def _needs_age(a):
    return not _is_kids(a)


Q = [
    dict(id="topic", kind="text", required=True, field="topic", ar="ما فكرة الفيديو؟ (موضوع واحد واضح)", en="What is the video about?"),
    dict(id="project_type", kind="choice", required=True, field="project_type", options=TYPES, ar="ما نوع المحتوى؟", en="What kind of content is it?"),
    dict(id="letter", kind="text", required=True, field="letter", applies=_is_alpha, ar="أي حرف سنعلّم؟ (حرف واحد)", en="Which letter?"),
    dict(id="age_band", kind="choice", required=True, field="audience.age_band", options=AGES, applies=_needs_age,
         default="adult", ar="من الجمهور المستهدف؟", en="Who is the audience?"),
    dict(id="level", kind="choice", required=False, field="audience.level", options=LEVELS, default="beginner",
         ar="ما المستوى التعليمي؟", en="Educational level?"),
    dict(id="language", kind="choice", required=True, field="language", options=LANGS, default="ar", ar="ما لغة الفيديو؟", en="Language?"),
    dict(id="dialect", kind="text", required=False, field="dialect", default="الفصحى المعاصرة",
         applies=lambda a: a.get("language", "ar") != "en", ar="أي لهجة؟ (الافتراضي: الفصحى)", en="Dialect?"),
    dict(id="duration", kind="choice", required=True, field="duration", options=DURATIONS, default="300", ar="ما مدة الفيديو؟", en="Duration?"),
    dict(id="duration_seconds", kind="number", required=True, field="duration.seconds", applies=lambda a: a.get("duration") == "custom",
         ar="كم ثانية بالضبط؟", en="Exact seconds?"),
    dict(id="visual_style", kind="choice", required=True, field="visual_style", options=None, default="classroom_2d_cartoon",
         ar="أي نمط بصري؟", en="Visual style?"),
    dict(id="narration", kind="choice", required=True, field="narration.mode", options=NARR, default="human_recording",
         ar="كيف سيكون الصوت؟", en="How will narration be produced?"),
    dict(id="aspect", kind="choice", required=False, field="format.aspect", options=ASPECTS, default="16:9",
         ar="النسبة والمنصة؟", en="Aspect ratio / platform?"),
    dict(id="quality", kind="choice", required=False, field="quality", options=QUALITY, default="standard", ar="جودة الإنتاج؟", en="Production quality?"),
    dict(id="available_assets", kind="list", required=False, field="available_assets", default=[],
         ar="هل لديك أصول جاهزة (شعار، صور، تسجيلات)؟", en="Existing assets?"),
    dict(id="budget_usd", kind="number", required=False, field="constraints.budget_usd", default=0,
         ar="هل من ميزانية للمزوّدين الخارجيين؟ (0 = بلا إنفاق)", en="Budget for external providers (USD)?"),
    dict(id="must_have", kind="list", required=False, field="must_have", default=[], ar="أي شيء يجب أن يتضمنه؟", en="Must-haves?"),
    dict(id="avoid", kind="list", required=False, field="avoid", default=[], ar="أي شيء يجب تجنبه؟", en="Avoid?"),
    dict(id="workflow", kind="choice", required=False, field="workflow", options=WORKFLOWS, default="approval", ar="كيف تريد سير العمل؟", en="Workflow mode?"),
]
BY_ID = {q["id"]: q for q in Q}


class InterviewError(ValueError):
    pass


def detect(topic):
    """اقتراحات من نص الموضوع (ليست إجابات): تحتاج تأكيد المستخدم."""
    sug = {}
    m = re.search(r"حرف\s+(?:ال)?(\S)", topic)
    if m:
        ch = "ا" if m.group(1) in _L.ALIF_FAMILY else m.group(1)
        if ch in _L.LETTERS:
            sug["letter"] = ch
    if re.search(r"حرف|حروف|أبجدي|ابجدي|أطفال|اطفال", topic):
        sug["project_type"] = "kids_education"
    return sug


def _set(d, path, v):
    cur = d
    parts = path.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = v


class Interview:
    def __init__(self, path=None, styles=None):
        self.path = Path(path) if path else None
        self.styles = styles or StyleManager()
        self.s = {"answers": {}, "defaulted": [], "summary_shown": False, "confirmed_by": None}
        if self.path and self.path.exists():
            self.s = json.loads(self.path.read_text("utf-8"))

    def _save(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.s, ensure_ascii=False, indent=2), "utf-8")

    @property
    def a(self):
        return self.s["answers"]

    def _options(self, q):
        if q["id"] == "visual_style":
            return {sid: f"{st['name_ar']} — {'يُصيَّر محلياً' if st['render_support'] == 'native' else 'جزئي محلياً' if st['render_support'] == 'partial' else 'يحتاج مزوّداً (غير متاح حالياً)'}"
                    for sid, st in self.styles.all().items()}
        return q.get("options")

    def applicable(self):
        return [q for q in Q if q.get("applies", lambda a: True)(self.a)]

    def next_question(self):
        """أول سؤال منطبق لم يُجَب ومطلوب أو له افتراض غير مقبول بعد. سؤال واحد فقط."""
        for q in self.applicable():
            if q["id"] not in self.a:
                out = {"id": q["id"], "ask_ar": q["ar"], "ask_en": q["en"], "kind": q["kind"], "required": q["required"],
                       "options": self._options(q), "default": q.get("default")}
                if q["id"] == "topic":
                    out["note"] = "اسأل عن الفكرة أولاً؛ لا تولّد شيئاً قبل فهمها."
                if q["id"] in ("project_type", "letter") and self.a.get("topic"):
                    sug = detect(self.a["topic"]).get(q["id"])
                    if sug:
                        out["suggestion"] = sug
                return out
        return None

    def answer(self, qid, value):
        q = BY_ID.get(qid)
        if q is None:
            raise InterviewError(f"unknown question {qid}")
        if q not in self.applicable():
            raise InterviewError(f"question '{qid}' does not apply to the current answers")
        opts = self._options(q)
        if q["kind"] == "choice" and str(value) not in {str(k) for k in opts}:
            raise InterviewError(f"'{value}' is not a valid option for {qid}: {list(opts)}")
        if q["kind"] == "number":
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise InterviewError(f"{qid} must be a number")
            if value < 0 or (qid == "duration_seconds" and value <= 0):
                raise InterviewError(f"{qid} out of range")
        if q["kind"] == "text":
            value = str(value).strip()
            if not value and q["required"]:
                raise InterviewError(f"{qid} cannot be empty")
            if qid == "letter":
                value = "ا" if value in _L.ALIF_FAMILY else value
                if value not in _L.LETTERS:
                    raise InterviewError("letter must be one of the 28 Arabic base letters (ا ب ت … ي)")
        if q["kind"] == "list":
            value = [str(x).strip() for x in (value if isinstance(value, list) else [value]) if str(x).strip()]
        self.a[qid] = value
        self.s["defaulted"] = [d for d in self.s["defaulted"] if d != qid]
        self.s["summary_shown"] = False       # أي تغيير يُبطل عرض الملخص السابق
        self.s["confirmed_by"] = None
        self._save()
        return self.next_question()

    def accept_default(self, qid):
        q = BY_ID[qid]
        if "default" not in q:
            raise InterviewError(f"'{qid}' has no default; it must be answered")
        self.answer(qid, q["default"])
        self.s["defaulted"].append(qid)
        self._save()
        return self.next_question()

    def missing_required(self):
        return [q["id"] for q in self.applicable() if q["required"] and q["id"] not in self.a]

    def to_project(self):
        miss = self.missing_required()
        if miss:
            raise InterviewError(f"required answers missing: {miss}")
        a = self.a
        p = {"project_type": a["project_type"], "topic": a["topic"], "language": a.get("language", "ar"),
             "audience": {"age_band": "child" if _is_kids(a) else a.get("age_band", "adult"), "level": a.get("level", "beginner")},
             "visual_style": a.get("visual_style", "classroom_2d_cartoon"), "workflow": a.get("workflow", "approval"),
             "narration": {"mode": a.get("narration", "human_recording")}, "format": {"aspect": a.get("aspect", "16:9")},
             "quality": a.get("quality", "standard"), "approved": bool(self.s["confirmed_by"])}
        if "letter" in a:
            p["letter"] = a["letter"]
        if "dialect" in a:
            p["dialect"] = a["dialect"]
        dur = a.get("duration", "300")
        p["duration"] = {"mode": "custom", "seconds": float(a["duration_seconds"]), "tolerance_pct": 10} if dur == "custom" \
            else {"mode": "fixed", "seconds": float(dur), "tolerance_pct": 10}
        if a.get("available_assets"):
            p["available_assets"] = a["available_assets"]
        bud = a.get("budget_usd", 0)
        p["constraints"] = {"budget_usd": bud, "no_external_providers": bud == 0}
        for k in ("must_have", "avoid"):
            if a.get(k):
                p[k] = a[k]
        p["assumptions"] = [f"افتراضي: {k} = {a.get(k)}" for k in self.s["defaulted"] if a.get(k) not in ([], "", 0, 0.0, None)]
        st = self.styles.get(p["visual_style"])
        if st["render_support"] == "provider_required":
            p["assumptions"].append(f"النمط «{st['name_ar']}» يحتاج مزوّد صور/فيديو غير متاح؛ سيُنتَج تخطيط ومواصفات فقط حتى يُحدَّد مزوّد")
        errs = validate_file(p, "project.schema.json")
        if errs:
            raise InterviewError("brief violates project.schema.json: " + "; ".join(errs[:4]))
        return p

    def summary(self, lang="ar"):
        p = self.to_project()
        self.s["summary_shown"] = True
        self._save()
        lines = [f"الموضوع: {p['topic']}" + (f" (الحرف: {p['letter']})" if "letter" in p else ""),
                 f"النوع: {TYPES[p['project_type']]} | الجمهور: {AGES[p['audience']['age_band']]} / {LEVELS[p['audience']['level']]}",
                 f"اللغة: {LANGS[p['language']]} | المدة: {int(p['duration']['seconds'])} ث (± {p['duration']['tolerance_pct']}%)",
                 f"النمط: {self.styles.get(p['visual_style'])['name_ar']} | الصوت: {NARR[p['narration']['mode']]}",
                 f"الميزانية للمزوّدين: {p['constraints']['budget_usd']} $ | سير العمل: {WORKFLOWS[p['workflow']]}"]
        if p["assumptions"]:
            lines.append("افتراضات تحتاج مراجعتك: " + " | ".join(p["assumptions"]))
        return "\n".join(lines)

    def confirm(self, actor):
        if not self.s["summary_shown"]:
            raise InterviewError("show the summary (summary()) to the user before confirming")
        if not actor or not actor.strip():
            raise InterviewError("actor required")
        self.s["confirmed_by"] = actor.strip()
        self._save()
        return self.to_project()
