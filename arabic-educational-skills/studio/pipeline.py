"""ربط الوكلاء بمراحل سير العمل الاثنتي عشرة. المراحل الإبداعية العامة تُسلَّم للمضيف (HostTask)؛ ودرس حروف الأطفال
يُنتَج حتمياً. لا مرحلة هنا تدّعي توليد ما لا يستطيعه الكود (صور/فيديو/صوت خارجيون)."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .agents import creative_director, qa, storyboard, subtitles
from .agents.research import ResearchLedger
from .core.orchestrator import FuncAgent, HostTask, NonRetriable
from .core.state import atomic_write
from .systems.asset_manager.manager import AssetManager
from .systems.kids_learning.alphabet import build_letter_lesson
from .systems.kids_learning.converter import lesson_to_master_script
from .systems.provider_manager.manager import ProviderManager, ProviderNotImplemented
from .systems.style_manager.manager import StyleManager

ROOT = Path(__file__).resolve().parents[1]
VIDEO = "video-01"


class PipelineError(NonRetriable):
    pass


def _brief(ctx):
    return ctx["inputs"]["interview"]


def _is_letter_lesson(brief):
    return brief["project_type"] == "kids_education" and "letter" in brief


def _video_dir(root):
    d = Path(root) / VIDEO
    d.mkdir(exist_ok=True)
    return d


def default_agents(project, styles=None, providers=None):
    root = project.root
    styles = styles or StyleManager(root / "styles")

    def interview_task():
        return HostTask("interviewer", "نفّذ المقابلة سؤالاً واحداً في كل مرة عبر studio.agents.interviewer.Interview ثم قدّم to_project() بعد confirm().")

    def creative(ctx):
        return creative_director.direct(_brief(ctx), styles)

    def research(ctx):
        b = _brief(ctx)
        if not _is_letter_lesson(b):
            raise_host("researcher", ctx, "ابحث عن الادعاءات الواقعية قبل الكتابة وسجّلها عبر ResearchLedger بمصادر حقيقية فقط؛ ميّز الحقيقة عن التفسير.")
        led = ResearchLedger(root / "research.json")
        if "bank" not in led.d["sources"]:
            led.add_source("bank", "Arabic vocabulary bank (project-internal)", citation="studio/systems/arabic_language/bank.py — unreviewed internal list",
                           reliability_note="غير معتمد؛ يحتاج مراجعة معلّم لغة عربية")
            led.add_claim(f"أمثلة الحرف {b['letter']} وأشكاله ومواضعه تُفحص بنيوياً بالكود؛ المعنى والنطق يحتاجان مراجع مختص", kind="uncertain", sources=["bank"], topic="orthography")
        return led.to_artifact()

    def script(ctx):
        b = _brief(ctx)
        if not _is_letter_lesson(b):
            raise_host("scriptwriter", ctx, "اكتب مشاهد بصيغة scene.schema.json ثم حوّلها عبر scriptwriter.to_master_script مع احترام مدة المشروع وسماحيتها.")
        d = b["duration"]
        lesson = build_letter_lesson(b["letter"], age_band=b["audience"]["age_band"], lang="ar" if b["language"] != "en" else "en",
                                     target_seconds=d["seconds"], tolerance=d.get("tolerance_pct", 10) / 100)
        atomic_write(root / "lesson.json", json.dumps(lesson, ensure_ascii=False, indent=2))
        doc = lesson_to_master_script(lesson)
        led = ResearchLedger(root / "research.json")
        led.add_lesson_review_items(lesson)
        if not lesson["duration_report"]["within_tolerance"]:
            raise PipelineError("lesson duration is outside tolerance: " + json.dumps(lesson["duration_report"], ensure_ascii=False))
        return doc

    def raise_host(name, ctx, instructions):
        HostTask(name, instructions).run(ctx)

    def story(ctx):
        b = _brief(ctx)
        sid = b["visual_style"]
        return storyboard.build_storyboard(ctx["inputs"]["script"], styles.get(sid) if sid in styles.all() else styles.get("classroom_2d_cartoon"))

    def assets_plan(ctx):
        b, sc = _brief(ctx), ctx["inputs"]["script"]
        pm = ProviderManager(b.get("constraints", {}))
        st = styles.get(b["visual_style"]) if b["visual_style"] in styles.all() else None
        items, blocked = [pm.estimate_item("local_engine", len(sc["scenes"]))], []
        if st and st["render_support"] == "provider_required":
            blocked.append(f"style '{st['id']}' needs an image/video provider; none implemented or allowed")
        if b["narration"]["mode"] == "tts_service":
            blocked.append("narration mode tts_service has no implemented provider")
        from .core.cost import CostManager
        return {"estimate": CostManager.estimate(items), "items": items, "blocked": blocked, "scenes": len(sc["scenes"]),
                "required_assets": sorted({a for s in ctx["inputs"]["storyboard"]["shots"] for a in s["required_assets"]}),
                "irreversible_operations": [], "note": "الإنفاق الخارجي صفر؛ التصيير المحلي مجاني. لا شيء يُنفَّذ قبل اعتمادك."}

    def visual(ctx):
        plan = ctx["inputs"]["asset_planning"]
        if plan["blocked"]:
            raise PipelineError("production blocked: " + " | ".join(plan["blocked"]))
        V = _video_dir(root)
        doc = ctx["inputs"]["script"]
        (V / "master-script.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), "utf-8")
        for sub in ("characters", "audio"):
            (root / sub).mkdir(exist_ok=True)
        for f in (ROOT / "engine" / "fonts").glob("*.woff2"):
            (root / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, root / "assets" / "fonts" / f.name)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_script.py"), str(V / "master-script.json"), "--update-hashes"],
                           capture_output=True, text=True)
        if r.returncode:
            raise PipelineError("script validation failed:\n" + r.stdout[-600:])
        r = subprocess.run([sys.executable, str(ROOT / "engine" / "build.py"), str(V), "silent", "--workers", "2"], capture_output=True, text=True)
        out = V / "exports" / "silent.mp4"
        if r.returncode or not out.exists():
            raise PipelineError("engine build failed:\n" + (r.stdout + r.stderr)[-800:])
        for s in ctx["inputs"]["script"]["scenes"]:
            ctx["cost"].charge("visual_production", "local_engine", 1, 0.0, s["id"])
        return {"video": str(out.relative_to(root)), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "scenes": len(doc["scenes"])}

    def voice(ctx):
        b = _brief(ctx)
        mode = b["narration"]["mode"]
        if mode == "subtitles_only":
            return {"mode": mode, "audio": None, "note": "لا صوت: الفيديو بترجمة مكتوبة فقط"}
        if mode == "tts_service":
            ProviderManager(b.get("constraints", {})).require("speech")      # يرمي ProviderNotImplemented
        from importlib import util
        spec = util.spec_from_file_location("aes_common", ROOT / "scripts" / "aes_common.py")
        m = util.module_from_spec(spec); spec.loader.exec_module(m)
        doc, missing, found = ctx["inputs"]["script"], [], []
        for sc in doc["scenes"]:
            for i, d in enumerate(sc.get("dialogue", []), 1):
                lid = m.line_id(sc, i, d)
                hit = next((p for e in ("wav", "mp3", "m4a", "ogg", "flac") if (p := root / "audio" / f"{lid}.{e}").exists()), None)
                (found if hit else missing).append(lid)
        if missing:
            raise PipelineError(f"{len(missing)} recording(s) missing in audio/ (first: {missing[:3]}). Run scripts/voice_pack.py to get the recording pack, record, then retry.")
        return {"mode": mode, "audio_files": len(found)}

    def editing(ctx):
        v = ctx["inputs"]["visual_production"]
        vp = root / v["video"]
        if not vp.exists():
            raise PipelineError("rendered video missing")
        final = root / "exports" / "edited.mp4"
        final.parent.mkdir(exist_ok=True)
        vo = ctx["inputs"]["voice_sound"]
        if vo.get("audio_files"):
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "mux_audio.py"), str(_video_dir(root)), "silent", str(root / "audio")], capture_output=True, text=True)
            voiced = _video_dir(root) / "exports" / "silent-voiced.mp4"
            if r.returncode or not voiced.exists():
                raise PipelineError("audio mux failed:\n" + (r.stdout + r.stderr)[-600:])
            shutil.copy2(voiced, final)
        else:
            shutil.copy2(vp, final)
        return {"video": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(), "voiced": bool(vo.get("audio_files"))}

    def subs(ctx):
        b = _brief(ctx)
        r = subtitles.build(ctx["inputs"]["script"], age=b["audience"]["age_band"])
        (root / "exports").mkdir(exist_ok=True)
        (root / "exports" / "subtitles.srt").write_text(r["srt"], "utf-8")
        (root / "exports" / "subtitles.vtt").write_text(r["vtt"], "utf-8")
        return {"srt": "exports/subtitles.srt", "vtt": "exports/subtitles.vtt", "cues": len(r["cues"]), "reading_speed_issues": r["issues"]}

    def quality(ctx):
        b = _brief(ctx)
        lesson = json.loads((root / "lesson.json").read_text("utf-8")) if (root / "lesson.json").exists() else None
        rep = qa.run_qa(project, master=ctx["inputs"]["script"], project_brief=b, lesson=lesson, export_path=root / ctx["inputs"]["editing"]["video"],
                        styles=styles, assets=AssetManager(root / "assets") if (root / "assets" / "registry.json").exists() else None)
        rep["subtitle_reading_speed_issues"] = ctx["inputs"]["subtitles"]["reading_speed_issues"]
        if not rep["passed"]:
            raise PipelineError("QA blockers: " + " | ".join(rep["blockers"][:6]))
        return rep

    def final(ctx):
        e = ctx["inputs"]["editing"]
        src = root / e["video"]
        dst = root / "exports" / "final" / "video.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"video": str(dst.relative_to(root)), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                "subtitles": ctx["inputs"]["subtitles"]["srt"], "qa_passed": ctx["inputs"]["qa"]["passed"],
                "needs_human": ctx["inputs"]["qa"]["needs_human"], "voiced": e["voiced"]}

    return {"interview": interview_task(), "creative_brief": FuncAgent("creative_director", creative), "research": FuncAgent("research", research),
            "script": FuncAgent("scriptwriter", script), "storyboard": FuncAgent("storyboard", story), "asset_planning": FuncAgent("asset_planner", assets_plan),
            "visual_production": FuncAgent("visual_director", visual), "voice_sound": FuncAgent("voice_director", voice),
            "editing": FuncAgent("video_editor", editing), "subtitles": FuncAgent("subtitle_agent", subs), "qa": FuncAgent("qa", quality),
            "final_export": FuncAgent("export", final)}
