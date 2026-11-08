"""خطة الدرس العامة (lesson-plan v1): درس في أي مادة ولأي عمر، مكتوب كقائمة كتل مكتوبة النوع.

المضيف (النموذج) يكتب الخطة من طلب المستخدم؛ هذا الملف يتحقق منها ويحسب توقيتها ويحوّلها إلى خصائص
يقرؤها محرك Remotion. لا يكتب محتوى ولا يحكم على صحته العلمية: هذا دور الكاتب والمراجع البشري.
"""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PLAN_VERSION = "1.0"
# Version of the props object handed to remotion/render.mjs. Bump the major
# part when a field changes meaning; render.mjs refuses a missing or unknown major.
PROPS_VERSION = "1.0"
# Version of the delivery sidecar written next to each rendered video (contract C7).
# A consumer must reject a sidecar whose major it does not implement.
SIDECAR_VERSION = "1.0"
AGE_BANDS = ("preschool", "child", "preteen", "teen", "adult")
# كلمات في الثانية للسرد (طبيعي، بطيء)
WPS = {"preschool": (1.45, 0.75), "child": (1.7, 0.8), "preteen": (2.0, 1.0), "teen": (2.4, 1.3), "adult": (2.6, 1.5)}
THINK = {"preschool": 5.0, "child": 4.0, "preteen": 3.5, "teen": 3.0, "adult": 3.0}      # مهلة التفكير في السؤال
REPEAT = {"preschool": 2.5, "child": 2.2, "preteen": 1.8, "teen": 1.5, "adult": 1.5}     # وقفة الترديد لكل مرة
MAX_BLOCK = {"preschool": 20, "child": 25, "preteen": 35, "teen": 45, "adult": 60}      # تنبيه: كتلة طويلة على العمر
THEMES = ("classroom", "chalkboard", "paper", "minimal", "night")
FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
AVATARS = ("letter_buddy", "none")
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".ogg")
FPS = 30
MIN_VISUAL = 2.0

# النوع ← (الحقول المطلوبة، الحقول النصية المعروضة للفحص)
BLOCKS = {
    "title":       (("heading",), ("heading", "subheading")),
    "explain":     ((), ("heading", "text", "bullets")),
    "term":        (("term", "definition"), ("term", "definition")),
    "example":     (("text",), ("text", "caption")),
    "compare":     (("left", "right"), ()),
    "steps":       (("items",), ("heading", "items")),
    "image":       (("concept",), ("caption",)),
    "letter":      (("letter",), ()),
    "word":        (("word",), ("word", "caption")),
    "say_with_me": (("text",), ("text",)),
    "quiz":        (("question", "options", "answer_index"), ("question", "options")),
    "recap":       (("points",), ("heading", "points")),
    "outro":       ((), ("text",)),
}
ARABIC_LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
HARAKAT = set("ًٌٍَُِّْٰ")
LOOKALIKES = {"ی": "ي", "ک": "ك", "ہ": "ه", "ے": "ي", "ھ": "ه"}
DOUBLE_VOWEL = re.compile("[ًٌٍَُِْ][ًٌٍَُِْ]")
DOUBLE_SHADDA = re.compile("ّ[ًٌٍَُِْ]?ّ")
HAS_AR = re.compile("[؀-ۿ]")
MAX_ONSCREEN = {"16:9": 140, "9:16": 100, "1:1": 110}   # حروف لكل نص معروض قبل التنبيه


class PlanError(ValueError):
    pass


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def strip_marks(s):
    return "".join(c for c in nfc(s) if c not in HARAKAT)


def words(s):
    return [w for w in re.split(r"\s+", strip_marks(s).strip()) if w]


def load(path):
    return json.loads(Path(path).read_text("utf-8"))


# ------------------------------------------------------------------ فحص النص العربي
def check_arabic(path, text, errors, warnings, need_diacritics=True):
    if not text or not HAS_AR.search(text):
        return
    t = nfc(text)
    bad = sorted({c for c in t if c in LOOKALIKES})
    if bad:
        errors.append(f"{path}: حروف فارسية/أردية بدل العربية: " + "، ".join(f"{c}→{LOOKALIKES[c]}" for c in bad))
    if DOUBLE_VOWEL.search(t):
        errors.append(f"{path}: حركتان على حرف واحد")
    if DOUBLE_SHADDA.search(t):
        errors.append(f"{path}: شدة مكررة")
    if "ـ" in t:
        warnings.append(f"{path}: تطويل (ـ)")
    if need_diacritics and not any(c in HARAKAT for c in t) and any(len(HAS_AR.findall(w)) > 2 for w in t.split()):
        warnings.append(f"{path}: نص عربي بلا تشكيل (السرد يُقرأ بصوت ويُعرض مشكولاً للمتعلم)")


def _texts(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


# ------------------------------------------------------------------ المقاطع الزمنية للكتلة
def segments(block, age):
    """تسلسل الكتلة: كلام → (وقفة) → كلام. كل مقطع كلام له معرّف ثابت يُسمّى به ملف الصوت."""
    bid, ty = block["id"], block["type"]
    segs = []
    if block.get("narration"):
        segs.append({"kind": "speech", "id": bid, "text": block["narration"], "delivery": block.get("delivery", "natural")})
    if ty == "quiz":
        segs.append({"kind": "pause", "label": "think", "seconds": float(block.get("think_seconds", THINK[age]))})
        segs.append({"kind": "speech", "id": f"{bid}__answer", "text": block.get("answer_narration") or _default_answer(block),
                     "delivery": "natural", "label": "reveal"})
    elif ty == "say_with_me":
        reps = int(block.get("repeat", 1))
        for r in range(reps):
            segs.append({"kind": "speech", "id": f"{bid}__say{r + 1}" if r else f"{bid}__say", "text": block["text"],
                         "delivery": "slow", "label": "model"})
            segs.append({"kind": "pause", "label": "repeat", "seconds": float(block.get("pause_seconds", REPEAT[age]))
                         + 0.25 * len(words(block["text"]))})
    if block.get("narration_after") and ty != "quiz":
        segs.append({"kind": "speech", "id": f"{bid}__after", "text": block["narration_after"], "delivery": "natural"})
    if block.get("hold_seconds"):
        segs.append({"kind": "pause", "label": "hold", "seconds": float(block["hold_seconds"])})
    return segs


def _default_answer(b):
    opts = b.get("options") or []
    i = b.get("answer_index", 0)
    ans = opts[i] if isinstance(i, int) and 0 <= i < len(opts) else ""
    return f"الْإِجَابَةُ الصَّحِيحَةُ: {ans}." if ans else "الْإِجَابَةُ الصَّحِيحَةُ."


def speech_seconds(text, age, delivery="natural", lang="ar"):
    n = max(1, len(words(text)))
    nat, slow = WPS[age]
    wps = slow if delivery == "slow" else nat
    if lang != "ar":
        wps *= 1.35
    return round(n / wps + 0.4, 2)


def audio_seconds(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip())
    except Exception:
        return None


def find_audio(audio_dir, seg_id):
    if not audio_dir:
        return None
    for ext in AUDIO_EXT:
        p = Path(audio_dir) / f"{seg_id}{ext}"
        if p.exists():
            return p
    return None


def timeline(plan, audio_dir=None):
    """يحسب توقيت كل مقطع وكتلة. الصوت المسجّل الأطول من التقدير يمدّد المقطع (لا يُقص ولا يُسرّع)."""
    age = plan["audience"].get("age_band", "child")
    lang = plan["audience"].get("lang", "ar")
    t, out, missing = 0.0, [], []
    for b in plan["blocks"]:
        segs, bt = [], 0.0
        for s in segments(b, age):
            s = dict(s)
            if s["kind"] == "speech":
                est = speech_seconds(s["text"], age, s.get("delivery", "natural"), lang)
                ap = find_audio(audio_dir, s["id"])
                ad = audio_seconds(ap) if ap else None
                if audio_dir and not ap:
                    missing.append(s["id"])
                s["seconds"] = round((ad + 0.35) if ad else est, 2)
                if ap:
                    s["audio"] = str(Path(ap).resolve())
                    s["audio_seconds"] = ad
            s["start"] = round(bt, 2)
            bt += s["seconds"]
            segs.append(s)
        extra = 0.0
        if b["type"] == "steps":
            extra = 0.6 * len(b.get("items", []))
        dur = round(max(MIN_VISUAL, bt + extra, float(b.get("min_seconds", 0))) + 0.5, 2)   # 0.5 هواء بين الكتل
        out.append({"id": b["id"], "type": b["type"], "start": round(t, 2), "seconds": dur, "segments": segs})
        t += dur
    return {"total_seconds": round(t, 2), "blocks": out, "missing_audio": missing}


# ------------------------------------------------------------------ التحقق
def validate(plan):
    """يعيد (errors, warnings). الأخطاء تمنع التصيير."""
    E, W = [], []
    if plan.get("plan_version") != PLAN_VERSION:
        E.append(f"plan_version يجب أن يكون {PLAN_VERSION}")
    for k in ("title", "audience", "blocks"):
        if k not in plan:
            E.append(f"حقل مطلوب مفقود: {k}")
    if E:
        return E, W
    aud = plan["audience"]
    age = aud.get("age_band")
    if age not in AGE_BANDS:
        E.append(f"audience.age_band يجب أن يكون واحداً من {AGE_BANDS}")
        return E, W
    style = plan.get("style", {})
    if style.get("theme", "classroom") not in THEMES:
        E.append(f"style.theme غير معروف: {style.get('theme')} (المتاح: {', '.join(THEMES)})")
    for f in plan.get("formats", ["16:9"]):
        if f not in FORMATS:
            E.append(f"صيغة غير مدعومة: {f} (المتاح: {', '.join(FORMATS)})")
    av = plan.get("narrator", {}).get("avatar", "letter_buddy")
    if av not in AVATARS:
        E.append(f"narrator.avatar غير مدعوم: {av} (المتاح: {', '.join(AVATARS)})")
    al = plan.get("narrator", {}).get("avatar_letter", "ض")
    if av == "letter_buddy" and al not in ARABIC_LETTERS:
        E.append(f"narrator.avatar_letter يجب أن يكون حرفاً عربياً أساسياً: {al}")
    check_arabic("title", plan["title"], E, W, need_diacritics=False)

    ids, blocks = set(), plan["blocks"]
    if not blocks:
        E.append("لا توجد كتل")
    for i, b in enumerate(blocks):
        p = f"blocks[{i}]"
        ty = b.get("type")
        if ty not in BLOCKS:
            E.append(f"{p}: نوع غير معروف {ty!r} (المتاح: {', '.join(BLOCKS)})")
            continue
        bid = b.get("id")
        if not bid or not re.fullmatch(r"[A-Za-z0-9_\-]+", bid) or "__" in bid:
            E.append(f"{p}: id مطلوب بحروف لاتينية/أرقام/ـ/- وبلا '__' (يُسمّى به ملف الصوت)")
        elif bid in ids:
            E.append(f"{p}: id مكرر {bid}")
        ids.add(bid)
        req, shown = BLOCKS[ty]
        for k in req:
            if b.get(k) in (None, "", []):
                E.append(f"{p} ({ty}): الحقل {k} مطلوب")
        if ty not in ("say_with_me",) and not b.get("narration") and ty not in ("image",):
            W.append(f"{p} ({ty}): بلا narration — الكتلة صامتة")
        for k in shown:
            for j, s in enumerate(_texts(b.get(k))):
                check_arabic(f"{p}.{k}" + (f"[{j}]" if isinstance(b.get(k), list) else ""), s, E, W)
                for fmt in plan.get("formats", ["16:9"]):
                    if len(s) > MAX_ONSCREEN.get(fmt, 160):
                        W.append(f"{p}.{k}: نص طويل على الشاشة ({len(s)} حرفاً) لصيغة {fmt} — قسّمه")
        for k in ("narration", "narration_after", "answer_narration"):
            if b.get(k):
                check_arabic(f"{p}.{k}", b[k], E, W)
        _type_checks(p, b, plan, E, W)

    if not E:
        tl = timeline(plan)
        for b in tl["blocks"]:
            if b["seconds"] > MAX_BLOCK[age]:
                W.append(f"{b['id']}: {b['seconds']}ث طويلة لعمر {age} (الحد المقترح {MAX_BLOCK[age]}ث) — قسّمها")
        tgt = plan.get("target_seconds")
        if tgt:
            dev = (tl["total_seconds"] - tgt) / tgt
            if abs(dev) > plan.get("tolerance", 0.15):
                W.append(f"المدة المقدّرة {tl['total_seconds']}ث بعيدة عن الهدف {tgt}ث ({dev:+.0%})")
        types = [b["type"] for b in blocks]
        if age in ("preschool", "child") and "quiz" not in types and "say_with_me" not in types:
            W.append("درس للأطفال بلا تفاعل (quiz أو say_with_me)")
        if "recap" not in types and len(blocks) > 6:
            W.append("لا يوجد تلخيص (recap)")
    return E, W


def _type_checks(p, b, plan, E, W):
    ty = b["type"]
    if ty == "quiz":
        opts, ai = b.get("options") or [], b.get("answer_index")
        if not 2 <= len(opts) <= 4:
            E.append(f"{p}: عدد الخيارات بين 2 و4")
        if not isinstance(ai, int) or not 0 <= ai < len(opts):
            E.append(f"{p}: answer_index خارج الخيارات")
        if len({nfc(o) for o in opts}) != len(opts):
            E.append(f"{p}: خيارات مكررة")
        q = b.get("question", "")
        q_words = [re.sub(r"[^\w]", "", w) for w in words(q)]          # الجواب كلمةً مستقلة في نص السؤال
        if isinstance(ai, int) and 0 <= ai < len(opts) and b.get("listening") and strip_marks(opts[ai]).strip() in q_words:
            E.append(f"{p}: سؤال استماع يكتب الإجابة على الشاشة")
    if ty == "example":
        for h in b.get("highlight", []):
            if nfc(h) not in nfc(b["text"]):
                E.append(f"{p}: التلوين «{h}» غير موجود حرفياً (بتشكيله) في النص")
        if b.get("status") not in (None, "right", "wrong", "neutral"):
            E.append(f"{p}: status يجب أن يكون right أو wrong أو neutral")
    if ty == "compare":
        for side in ("left", "right"):
            s = b.get(side) or {}
            if not s.get("text"):
                E.append(f"{p}.{side}: text مطلوب")
            check_arabic(f"{p}.{side}.text", s.get("text", ""), E, W)
            check_arabic(f"{p}.{side}.label", s.get("label", ""), E, W, need_diacritics=False)
    if ty == "letter":
        if b["letter"] not in ARABIC_LETTERS:
            E.append(f"{p}: letter يجب أن يكون حرفاً عربياً أساسياً")
    if ty == "word":
        hl = b.get("highlight_letters", [])
        n = len([c for c in nfc(b["word"]) if c.isalpha()])
        if any(not isinstance(i, int) or not 0 <= i < n for i in hl):
            E.append(f"{p}: highlight_letters خارج حروف الكلمة")
    if ty == "steps" and len(b.get("items", [])) > 6:
        W.append(f"{p}: أكثر من 6 خطوات في كتلة واحدة")
    if ty == "recap" and len(b.get("points", [])) > 5:
        W.append(f"{p}: أكثر من 5 نقاط تلخيص")
    if ty == "image" and not b.get("asset"):
        W.append(f"{p}: صورة بلا asset — ستظهر بطاقة محجوزة باسم المفهوم")
    if b.get("asset"):
        if not Path(b["asset"]).exists():
            E.append(f"{p}: ملف الصورة غير موجود: {b['asset']}")


# ------------------------------------------------------------------ خصائص المحرك
def render_props(plan, fmt, audio_dir=None, captions=True):
    """يحوّل الخطة + التوقيت إلى خصائص Remotion (إطارات، أبعاد، نصوص الترجمة، مسارات الصوت)."""
    if fmt not in FORMATS:
        raise PlanError(f"unknown format {fmt}")
    w, h = FORMATS[fmt]
    tl = timeline(plan, audio_dir)
    by_id = {b["id"]: b for b in plan["blocks"]}
    blocks, caps, audio = [], [], []
    for tb in tl["blocks"]:
        b = by_id[tb["id"]]
        f0 = round(tb["start"] * FPS)
        segs = []
        for s in tb["segments"]:
            s0 = f0 + round(s["start"] * FPS)
            s1 = s0 + round(s["seconds"] * FPS)
            segs.append({**{k: v for k, v in s.items() if k not in ("audio",)}, "from": s0 - f0, "to": s1 - f0})
            if s["kind"] == "speech":
                if s.get("audio"):
                    audio.append({"src": "audio/" + Path(s["audio"]).name, "from": s0,
                                  "frames": round((s.get("audio_seconds") or s["seconds"]) * FPS) + 2})
                if captions and not (b["type"] == "quiz" and b.get("listening") and s.get("label") != "reveal"):
                    caps += _caption_chunks(s.get("caption") or b.get("caption_override") or s["text"], s0,
                                            s0 + round((s.get("audio_seconds") or s["seconds"] - 0.3) * FPS))
                elif captions:
                    caps += _caption_chunks(b.get("caption_override") or "…", s0, s1)
        blocks.append({**b, "from": f0, "frames": round(tb["seconds"] * FPS), "segments": segs})
    total = blocks[-1]["from"] + blocks[-1]["frames"] if blocks else FPS
    speaking = [[a["from"], a["from"] + a["frames"]] for a in audio] or \
               [[blk["from"] + s["from"], blk["from"] + s["to"] - 6] for blk in blocks for s in blk["segments"] if s["kind"] == "speech"]
    return {"props_version": PROPS_VERSION, "fps": FPS, "width": w, "height": h, "format": fmt, "durationInFrames": total,
            "title": plan["title"], "theme": plan.get("style", {}).get("theme", "classroom"),
            "accent": plan.get("style", {}).get("accent"), "age_band": plan["audience"]["age_band"],
            "narrator": {"avatar": plan.get("narrator", {}).get("avatar", "letter_buddy"),
                         "letter": plan.get("narrator", {}).get("avatar_letter", "ض"),
                         "name": plan.get("narrator", {}).get("name", "")},
            "blocks": blocks, "captions": caps if captions else [], "audio": audio,
            "speaking": speaking, "has_audio": bool(audio), "music": None}


def _caption_chunks(text, f0, f1, max_chars=46):
    ws = nfc(text).split()
    chunks, cur = [], ""
    for w in ws:
        if cur and len(cur) + 1 + len(w) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    if not chunks:
        return []
    total = sum(len(c) for c in chunks)
    out, f = [], f0
    for c in chunks:
        n = max(12, round((f1 - f0) * len(c) / total))
        out.append({"text": c, "from": f, "to": min(f1, f + n)})
        f += n
    return out


def srt(props):
    def ts(fr):
        s = fr / props["fps"]
        return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(round((s % 1) * 1000)) % 1000:03d}"
    return "\n".join(f"{i}\n{ts(c['from'])} --> {ts(c['to'])}\n{c['text']}\n" for i, c in enumerate(props["captions"], 1))


SIDECAR_REQUIRED = ("sidecar_version", "slug", "title", "format", "video", "seconds", "has_audio")


def sidecar(plan, fmt, video, srt=None, seconds=None, has_audio=None, technical_check=None):
    """بطاقة تسليم مُرقّمة الإصدار (عقد C7) تُكتب بجانب الفيديو بدل الاعتماد على اسم المجلد.

    `video` و`srt` اسمان فقط (بلا مسار): البطاقة تفترض أنهما في مجلدها نفسه.
    """
    return {
        "sidecar_version": SIDECAR_VERSION,
        "slug": plan.get("slug") or "lesson",
        "title": plan["title"],
        "subject": plan.get("subject"),
        "age_band": plan["audience"]["age_band"],
        "lang": plan["audience"].get("lang", "ar"),
        "plan_version": plan.get("plan_version"),
        "format": fmt,
        "width": FORMATS[fmt][0],
        "height": FORMATS[fmt][1],
        "seconds": seconds,
        "has_audio": has_audio,
        "video": Path(video).name,
        "subtitles": Path(srt).name if srt else None,
        "technical_check": technical_check,
    }


def check_sidecar(doc):
    """يتحقق من بطاقة تسليم قبل أن يستهلكها ناشر. يعيد قائمة أخطاء (فارغة = صالحة)."""
    E = []
    ver = doc.get("sidecar_version")
    if not ver:
        E.append("sidecar_version مفقود")
    elif str(ver).split(".")[0] != SIDECAR_VERSION.split(".")[0]:
        E.append(f"sidecar_version غير مدعوم: {ver} (المدعوم {SIDECAR_VERSION}.x)")
    for k in SIDECAR_REQUIRED:
        if doc.get(k) in (None, ""):
            E.append(f"حقل مطلوب مفقود: {k}")
    if doc.get("format") and doc["format"] not in FORMATS:
        E.append(f"صيغة غير مدعومة: {doc['format']}")
    for k in ("video", "subtitles"):
        if doc.get(k) and Path(doc[k]).name != doc[k]:
            E.append(f"{k} يجب أن يكون اسم ملف داخل مجلد البطاقة")
    if doc.get("slug") and doc.get("video") and not doc["video"].startswith(doc["slug"] + "-"):
        E.append("video لا يطابق الشكل <slug>-<format>")
    return E


def voice_lines(plan):
    """قائمة أسطر التسجيل: معرّف الملف، النص المشكول، الوقت المقدّر."""
    age = plan["audience"]["age_band"]
    lines = []
    for b in plan["blocks"]:
        for s in segments(b, age):
            if s["kind"] == "speech":
                lines.append({"id": s["id"], "block": b["id"], "text": s["text"],
                              "estimate_seconds": speech_seconds(s["text"], age, s.get("delivery", "natural"))})
    return lines
