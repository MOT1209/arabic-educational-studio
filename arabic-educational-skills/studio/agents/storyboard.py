"""محرك اللوحة القصصية: master-script → لقطات (storyboard.schema.json). حتمي. مجموع مدد لقطات كل مشهد = مدة المشهد.
generation_prompt مواصفة نصية لمزوّد صور/فيديو (غير منفَّذ حالياً): لا يُنتَج بها شيء من تلقاء نفسه."""
from ..core.schema import validate_file

ARABIC_NOTE = ("لا تطلب من نموذج الصور رسم نص عربي داخل الصورة (يشوّه الحروف)؛ يُضاف النص العربي في المونتاج فوق اللقطة.")
SHOT_CYCLE = [("medium", "eye_level", "static"), ("close_up", "eye_level", "zoom"), ("medium", "over_shoulder", "static")]


def _split(duration, n):
    base = round(duration / n, 2)
    parts = [base] * (n - 1)
    parts.append(round(duration - sum(parts), 2))
    return parts


def build_storyboard(master, style, assets=None):
    """style: قاموس نمط من StyleManager. assets: معرّفات أصول متاحة (تُدرج في required_assets)."""
    shots, no = [], 0
    chars = {c["id"]: c for c in master.get("characters", [])}
    for sc in master["scenes"]:
        dur = sc["duration_seconds"]
        n = 1 if dur < 4 else 2 if dur < 9 else 3 if dur < 18 else 4
        durs = _split(dur, n)
        speakers = [d["character"] for d in sc.get("dialogue", [])] or sc.get("characters", [])
        letter_card = any(v["type"] in ("letter_card", "letter_highlight") for v in sc.get("visuals", []))
        for i in range(n):
            no += 1
            if i == 0:
                stype, angle, move = "establishing" if sc["id"] == master["scenes"][0]["id"] else "wide", "eye_level", "static"
            elif letter_card and i == 1:
                stype, angle, move = "close_up", "eye_level", "static"
            else:
                stype, angle, move = SHOT_CYCLE[(i - 1) % len(SHOT_CYCLE)]
            who = speakers[min(i, len(speakers) - 1)] if speakers else "none"
            subject = "السبورة والحرف" if letter_card and stype == "close_up" else (chars.get(who, {}).get("name") or who)
            req = [f"char_{c}" for c in sc.get("characters", [])] + [f"bg_{sc.get('background', 'classroom')}"]
            if assets is not None:
                req = [r for r in req]  # تُترك كما هي؛ التحقق من التوفر في مرحلة تخطيط الأصول
            shots.append({
                "shot_number": no, "scene_id": sc["id"], "shot_type": stype, "camera_angle": angle, "camera_movement": move,
                "subject": subject, "background": sc.get("background", "classroom"),
                "lighting": "إضاءة ثابتة متسقة مع بقية المشاهد", "composition": "السبورة في الوسط والشخصية على الجانب" if stype != "close_up" else "العنصر التعليمي يملأ الإطار",
                "character_position": "ثابت كما في بطاقة الشخصية", "visual_action": sc.get("learning_goal", ""),
                "duration_seconds": durs[i], "transition": sc.get("transition") or ("fade" if i == n - 1 and sc is master["scenes"][-1] else "cut"),
                "required_assets": req,
                "generation_prompt": f"{style['visual_instructions']} لقطة {stype} بزاوية {angle} وحركة {move}: {sc.get('learning_goal', '')}. {ARABIC_NOTE}",
                "continuity_notes": "حافظ على نفس الشخصيات ونسبها وألوان ملابسها وخلفية الفصل في كل اللقطات؛ لا تغيّر جنس الشخصية بين المشاهد.",
            })
    sb = {"version": "1", "style_id": style["id"], "shots": shots}
    errs = validate_file(sb, "storyboard.schema.json")
    if errs:
        raise ValueError("storyboard invalid: " + "; ".join(errs[:3]))
    return sb


def check_storyboard(sb, master, tol=0.05):
    issues = []
    for sc in master["scenes"]:
        s = sum(x["duration_seconds"] for x in sb["shots"] if x["scene_id"] == sc["id"])
        if abs(s - sc["duration_seconds"]) > tol:
            issues.append(f"{sc['id']}: shots total {s:.2f}s != scene {sc['duration_seconds']}s")
    nums = [x["shot_number"] for x in sb["shots"]]
    if nums != list(range(1, len(nums) + 1)):
        issues.append("shot numbers are not sequential")
    return issues
