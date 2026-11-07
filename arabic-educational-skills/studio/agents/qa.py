"""وكيل الجودة: يجمع فحوصاً حتمية فقط ويعيد blockers/warnings. لا يدّعي فحص ما لا يستطيع (المعنى، النطق، جودة الصورة)؛
تلك تُسرد في needs_human."""
import json
import subprocess
from pathlib import Path

from ..core import workflow as W
from ..core.approvals import Approvals
from ..core.schema import validate_file
from ..systems.arabic_language.orthography import validate_sentence
from ..systems.style_manager.manager import StyleManager

ROOT = Path(__file__).resolve().parents[2]


def _scripts_validator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_script", ROOT / "scripts" / "validate_script.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def probe_duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=60)
        return float(out.stdout.strip())
    except Exception:
        return None


def run_qa(project, *, master=None, project_brief=None, lesson=None, export_path=None, styles=None, providers=None, assets=None):
    blockers, warnings, needs_human, info = [], [], [], {}
    # 1) الاعتمادات وسلسلتها
    ap = Approvals(project)
    chain = ap.verify()
    if chain:
        blockers.append(f"approval log integrity: {chain[:2]}")
    for s in W.STAGES:
        if s.approval and s.id != "final_export" and W.index(s.id) < W.index("qa") and project.status(s.id) != "approved":
            blockers.append(f"stage '{s.id}' requires approval (status: {project.status(s.id)})")
    # 2) السيناريو
    if master:
        errs = validate_file(master, "master-script.schema.json")
        blockers += [f"script schema: {e}" for e in errs[:5]]
        try:
            v = _scripts_validator()
            e2, w2 = [], []
            v.semantic_checks(master, e2, w2)
            blockers += [f"script: {e}" for e in e2]
            warnings += [f"script: {w}" for w in w2]
        except Exception as ex:  # pragma: no cover
            warnings.append(f"semantic validator unavailable: {ex}")
        total = sum(s["duration_seconds"] for s in master["scenes"])
        info["script_total_seconds"] = total
        if project_brief:
            tgt, tol = project_brief["duration"]["seconds"], project_brief["duration"].get("tolerance_pct", 10) / 100
            if not tgt * (1 - tol) <= total <= tgt * (1 + tol):
                blockers.append(f"duration {total:.0f}s outside ±{tol:.0%} of target {tgt:.0f}s")
        # 3) إملاء النصوص العربية
        bad_words, review = 0, 0
        for sc in master["scenes"]:
            texts = [d["text_diacritized"] for d in sc.get("dialogue", [])] + \
                    [v["text_diacritized"] for v in sc.get("visuals", []) if v.get("type") in ("arabic_text", "highlight") and v.get("text_diacritized")]
            for t in texts:
                if len([c for c in t if "ء" <= c <= "ي"]) < 2:
                    continue                              # حرف مفرد أو رمز
                r = validate_sentence(t, kids=bool(project_brief and project_brief["audience"]["age_band"] == "child"))
                for i in r["issues"]:
                    if i["severity"] == "error":
                        bad_words += 1
                        blockers.append(f"{sc['id']}: orthography '{i['code']}' in «{t[:30]}»")
                    elif i["severity"] == "review":
                        review += 1
        info["orthography_review_flags"] = review
    # 4) المراجعة البشرية للدرس
    if lesson:
        pend = lesson["review"]["needs_human_review"]
        info["lesson_items_pending_review"] = len(pend)
        if pend:
            needs_human.append(f"{len(pend)} lesson item(s) not signed by a human reviewer (pronunciation/meaning/vocabulary)")
    # 5) النمط والمزوّد
    styles = styles or StyleManager()
    if project_brief:
        vs = project_brief["visual_style"]
        if vs in styles.all() and styles.get(vs)["render_support"] == "provider_required":
            warnings.append(f"style '{vs}' needs an image/video provider; local output will not match it")
    # 6) الأصول
    if assets:
        blockers += [f"assets: {i}" for i in assets.verify()]
    # 7) الملف الناتج
    if export_path:
        p = Path(export_path)
        if not p.exists():
            blockers.append(f"export missing: {p}")
        else:
            d = probe_duration(p)
            info["export_seconds"] = d
            if d is None:
                warnings.append("could not probe export duration (ffprobe)")
            elif master and abs(d - info["script_total_seconds"]) > 1.0:
                blockers.append(f"export duration {d:.1f}s differs from script {info['script_total_seconds']:.1f}s")
    needs_human += ["visual quality of rendered frames (open and watch)", "audio clarity/pronunciation if voiced", "educational suitability for the age band"]
    return {"passed": not blockers, "blockers": blockers, "warnings": warnings, "needs_human": needs_human, "info": info}
