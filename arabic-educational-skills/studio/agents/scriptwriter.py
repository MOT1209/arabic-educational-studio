"""محرك السيناريو: مشاهد غنية (scene.schema.json) → فحص توقيت صريح → master-script متوافق مع المحرك.
لا يولّد سيناريو قصيراً لفيديو طويل: إن نقص المحتوى يرفع TooShort مع عدد الثواني الناقصة بدل التمديد الصامت."""
from ..core.schema import validate_file
from ..engines import script_engine as SE

try:
    from engine.scriptlib import plain  # noqa: F401
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine"))
    from scriptlib import plain  # type: ignore

AVG_SCENE = {"child": 10, "preteen": 14, "teen": 18, "adult": 24}


class ScriptError(Exception):
    pass


class TooShort(ScriptError):
    def __init__(self, missing_seconds, hint):
        super().__init__(f"content is {missing_seconds:.0f}s short of the target; {hint}")
        self.missing_seconds = missing_seconds


class TooLong(ScriptError):
    pass


def scene_budget(target_seconds, age="child"):
    n = max(1, round(target_seconds / AVG_SCENE[age]))
    return {"suggested_scenes": n, "avg_scene_seconds": AVG_SCENE[age]}


def spoken_text(scene):
    parts = [scene.get("narration", "")] + [d["text"] for d in scene.get("dialogue", [])]
    return [p for p in parts if p and p.strip()]


def needed_seconds(scene, age="child"):
    """أقل مدة يحتاجها المشهد: كلام بسرعة عمر الجمهور + وقفة الترديد + نفَس."""
    t = sum(SE.speech_seconds(p, age) for p in spoken_text(scene))
    return round(t + scene.get("pause_for_repetition_seconds", 0) + 0.5, 2)


def check_scenes(scenes, target_seconds, tolerance=0.10, age="child"):
    issues, total = [], 0.0
    for i, sc in enumerate(scenes):
        errs = validate_file(sc, "scene.schema.json")
        if errs:
            issues.append({"scene": sc.get("scene_id", f"#{i}"), "severity": "error", "code": "schema", "detail": errs[:3]})
            continue
        need = needed_seconds(sc, age)
        total += sc["duration"]
        if sc["duration"] < need:
            issues.append({"scene": sc["scene_id"], "severity": "error", "code": "too_short_for_content",
                           "detail": f"duration {sc['duration']}s < needed {need}s"})
        words = sum(len(p.split()) for p in spoken_text(sc))
        if words and sc["duration"] > 0 and words / sc["duration"] > SE.WPS[age][0] * 1.25:
            issues.append({"scene": sc["scene_id"], "severity": "warning", "code": "speech_too_fast",
                           "detail": f"{words / sc['duration']:.1f} words/s > {SE.WPS[age][0] * 1.25:.1f}"})
    fit = SE.fit_report(total, target_seconds, tolerance)
    return {"issues": issues, "fit": fit, "ok": not any(i["severity"] == "error" for i in issues) and fit["within_tolerance"]}


def fit_durations(scenes, target_seconds, tolerance=0.10, age="child"):
    """يعدّل مدد المشاهد نسبياً إن أمكن دون النزول عن الحد الأدنى للمحتوى؛ وإلا يرفع TooShort/TooLong. لا يعدّل الأصل."""
    sc = [dict(s) for s in scenes]
    total = sum(s["duration"] for s in sc)
    lo, hi = target_seconds * (1 - tolerance), target_seconds * (1 + tolerance)
    if lo <= total <= hi:
        return sc
    if total < lo:
        extra = target_seconds - total
        raise TooShort(extra, f"add ≈{max(1, round(extra / AVG_SCENE[age]))} scene(s) or enrich content; padding silence is not done silently")
    floor = sum(needed_seconds(s, age) for s in sc)
    if floor > hi:
        raise TooLong(f"minimum content time {floor:.0f}s exceeds the allowed {hi:.0f}s; cut content")
    k = (target_seconds - floor) / max(1e-9, total - floor)
    for s in sc:
        need = needed_seconds(s, age)
        s["duration"] = round(need + (s["duration"] - need) * k, 2)
    return sc


def to_master_script(project, scenes, characters, *, references=None, target_level=None, subject="other"):
    """يبني master-script: السرد = السطر الأول للشخصية narrator (أو أول شخصية)، ثم الحوار؛ أزمنة متتابعة داخل المشهد."""
    age = project["audience"]["age_band"]
    narrator = next((c["id"] for c in characters if c["id"] == "narrator"), characters[0]["id"])
    out_scenes = []
    for sc in scenes:
        t, dlg, n = 0.4, [], 0
        for who, text in ([(narrator, sc["narration"])] if sc.get("narration", "").strip() else []) + [(d["character"], d["text"]) for d in sc.get("dialogue", [])]:
            n += 1
            dur = SE.speech_seconds(text, age) - 0.35
            end = round(t + max(SE.MIN_LINE - 0.35, dur), 2)
            if end > sc["duration"]:
                raise ScriptError(f"{sc['scene_id']}: speech runs past the scene end ({end}s > {sc['duration']}s)")
            dlg.append({"id": f"{sc['scene_id']}_{n:02d}", "character": who, "text_diacritized": text, "text_plain": plain(text),
                        "start": round(t, 2), "end": end})
            t = end + 0.35
        vis = []
        if sc.get("on_screen_text"):
            vis.append({"type": "arabic_text", "text_diacritized": sc["on_screen_text"], "text_plain": plain(sc["on_screen_text"]),
                        "direction": "rtl", "start": 0.3, "end": sc["duration"]})
        scene = {"id": sc["scene_id"], "duration_seconds": sc["duration"], "learning_goal": sc.get("educational_objective") or sc["purpose"],
                 "background": "classroom", "camera": sc.get("camera", "ثابتة"),
                 "characters": sorted({d["character"] for d in dlg}), "dialogue": dlg, "visuals": vis}
        if sc.get("transition"):
            scene["transition"] = sc["transition"]
        out_scenes.append(scene)
    doc = {"version": "1.0.0", "lesson": project["topic"], "subject": subject, "language": "ar", "target_level": target_level or
           {"child": "child", "preteen": "beginner", "teen": "intermediate", "adult": "advanced"}[age],
           "objectives": [project.get("learning_goal") or project["topic"]], "style": project["visual_style"],
           "characters": characters, "output": {"width": 1920, "height": 1080, "fps": 30, "formats": ["16:9"]}, "scenes": out_scenes}
    if references:
        doc["references"] = references
    errs = validate_file(doc, "master-script.schema.json")
    if errs:
        raise ScriptError("generated master script is invalid: " + "; ".join(errs[:4]))
    return doc
