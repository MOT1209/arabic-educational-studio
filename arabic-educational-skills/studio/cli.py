"""سطر أوامر الاستوديو:  python -m studio <command> ...   (كل المخرجات JSON أو نص عربي؛ رمز الخروج 0 = نجاح)."""
import argparse
import json
import sys
from pathlib import Path

from .agents import subtitles as subs_agent
from .agents.interviewer import Interview, InterviewError
from .core import workflow as W
from .core.approvals import Approvals, ApprovalError
from .core.orchestrator import Orchestrator
from .core.state import Project, StateError
from .systems.arabic_language.review import ReviewLedger
from .systems.arabic_language import review_sheet
from .systems.asset_manager.manager import AssetManager
from .systems.kids_learning.alphabet import build_letter_lesson
from .systems.kids_learning.converter import lesson_to_master_script
from .systems.kids_learning.to_plan import lesson_to_plan
from .lesson_plan import plan as LP
from .systems.provider_manager.manager import ProviderManager
from .systems.style_manager.manager import StyleManager


def out(o):
    print(json.dumps(o, ensure_ascii=False, indent=2))


def P(a):
    return Project(a.project)


def cmd_new(a):
    p = Project.create(a.project, a.name)
    out({"project_id": p.id, "root": str(p.root), "stages": W.ORDER})


def cmd_status(a):
    p = P(a)
    ap = Approvals(p)
    out({"project_id": p.id, "name": p.data["name"], "stages": {s: {"status": p.status(s), "revision": p.stage(s)["revision"],
         "approval_required": W.BY_ID[s].approval} for s in W.ORDER}, "next": ap.resume(), "approval_log_issues": ap.verify()})


def cmd_step(a):
    from .pipeline import default_agents
    p = P(a)
    o = Orchestrator(p, default_agents(p), budget_usd=a.budget)
    out(o.run_until_blocked() if a.until_blocked else o.step())


def cmd_submit(a):
    p = P(a)
    art = json.loads(Path(a.file).read_text("utf-8"))
    out({"stage": a.stage, "revision": p.submit(a.stage, art, author=a.actor)})


def cmd_decide(a):
    p = P(a)
    ap = Approvals(p)
    if a.cmd == "approve":
        out(ap.approve(a.stage, a.actor, a.revision, a.feedback or ""))
    elif a.cmd == "reject":
        out(ap.reject(a.stage, a.actor, a.feedback))
    elif a.cmd == "modify":
        art = json.loads(Path(a.file).read_text("utf-8")) if a.file else None
        out(ap.modify(a.stage, a.actor, a.feedback, art))
    elif a.cmd == "regenerate":
        out(ap.regenerate_section(a.stage, a.actor, a.section, a.feedback))
    elif a.cmd == "rewind":
        out(ap.rewind(a.stage, a.actor, a.feedback))


def cmd_compare(a):
    out(Approvals(P(a)).compare(a.stage, a.rev_a, a.rev_b))


def cmd_resume(a):
    out(Approvals(P(a)).resume())


def cmd_verify(a):
    p = P(a)
    issues = Approvals(p).verify()
    out({"approval_log_issues": issues})
    return 1 if issues else 0


def cmd_interview(a):
    iv = Interview(Path(a.project) / "interview.json", StyleManager(Path(a.project) / "styles"))
    if a.action == "next":
        out(iv.next_question() or {"done": True, "missing_required": iv.missing_required()})
    elif a.action == "answer":
        out(iv.answer(a.qid, a.value) or {"done": True})
    elif a.action == "default":
        out(iv.accept_default(a.qid) or {"done": True})
    elif a.action == "summary":
        print(iv.summary())
    elif a.action == "confirm":
        out(iv.confirm(a.actor))
    elif a.action == "submit":
        p = P(a)
        out({"revision": p.submit("interview", iv.to_project(), author=a.actor or "interviewer")})


def cmd_styles(a):
    m = StyleManager(Path(a.store))
    if a.action == "list":
        out([{"id": s["id"], "name_ar": s["name_ar"], "render_support": s["render_support"], "builtin": s["builtin"]} for s in m.all().values()])
    elif a.action == "preview":
        out(m.preview(a.id))
    elif a.action == "combine":
        out(m.combine(a.id, a.other, a.new_id, a.force))
    elif a.action == "duplicate":
        out(m.duplicate(a.id, a.new_id))
    elif a.action == "delete":
        m.delete(a.id)
        out({"deleted": a.id})
    elif a.action == "export":
        m.export(a.id, a.file)
        out({"exported": a.file})
    elif a.action == "import":
        out(m.import_file(a.file))


def cmd_providers(a):
    pm = ProviderManager()
    out(pm.health() if a.action == "health" else [{k: p[k] for k in ("id", "kind", "status", "notes")} for p in pm.list()])


def cmd_lesson(a):
    ledger = ReviewLedger(a.ledger) if a.ledger else None
    lesson = build_letter_lesson(a.letter, age_band=a.age, lang=a.lang, target_seconds=a.target, taught=tuple(a.taught or ""),
                                 ledger=ledger, profile=a.profile)
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    (d / "lesson.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=2), "utf-8")
    (d / "master-script.json").write_text(json.dumps(lesson_to_master_script(lesson), ensure_ascii=False, indent=2), "utf-8")
    (d / "lesson-plan.json").write_text(json.dumps(lesson_to_plan(lesson, theme=a.theme), ensure_ascii=False, indent=2), "utf-8")
    out({"letter": a.letter, "profile": a.profile, "duration": lesson["duration_report"], "warnings": [w["code"] for w in lesson["warnings"]],
         "pending_human_review": len(lesson["review"]["needs_human_review"]), "written": str(d)})


def cmd_plan(a):
    """خطة درس عامة لأي مادة: validate | timeline | voice | stills | render."""
    plan = LP.load(a.plan)
    E, W = LP.validate(plan)
    if a.action == "validate":
        out({"ok": not E, "errors": E, "warnings": W, "estimated_seconds": LP.timeline(plan)["total_seconds"] if not E else None})
        return 1 if E else 0
    if E:
        out({"ok": False, "errors": E, "warnings": W})
        return 1
    if a.action == "timeline":
        tl = LP.timeline(plan, a.audio)
        out({"total_seconds": tl["total_seconds"], "missing_audio": tl["missing_audio"],
             "blocks": [{"id": b["id"], "type": b["type"], "start": b["start"], "seconds": b["seconds"]} for b in tl["blocks"]]})
        return 0
    if a.action == "voice":
        lines = LP.voice_lines(plan)
        d = Path(a.out or "voice")
        d.mkdir(parents=True, exist_ok=True)
        md = ["# أسطر التسجيل", "", "سجّل كل سطر في ملف باسم معرّفه (wav أو mp3 أو m4a أو ogg) داخل مجلد واحد.",
              "الصوت الأطول من التقدير يمدّد الكتلة تلقائياً؛ لا تسرّع القراءة.", ""]
        for x in lines:
            md += [f"## `{x['id']}`  (~{x['estimate_seconds']}ث)", "", x["text"], ""]
        (d / "voice-lines.md").write_text("\n".join(md), "utf-8")
        (d / "voice-lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=2), "utf-8")
        out({"lines": len(lines), "written": str(d)})
        return 0
    from .lesson_plan import render as LR
    fmts = [f.strip() for f in a.formats.split(",")] if a.formats else None
    rep = LR.render(plan, a.out or "out", formats=fmts, audio_dir=a.audio, captions=not a.no_captions,
                    stills_only=a.action == "stills", concurrency=a.concurrency)
    out(rep)
    return 1 if any(o.get("technical_check") == "failed" for o in rep["outputs"]) else 0


def cmd_review(a):
    if a.action == "export":
        if not a.out:
            raise SystemExit("review export needs --out FILE.xlsx|FILE.csv")
        ledger = ReviewLedger(a.ledger) if a.ledger else None
        out(review_sheet.export_sheet(a.out, ledger=ledger, profile=a.profile))
        return 0
    if not a.ledger:
        raise SystemExit("--ledger is required")
    if a.action == "import":
        if not a.file:
            raise SystemExit("review import needs the sheet path")
        out(review_sheet.import_sheet(a.file, a.ledger, a.reviewer))
        return 0
    if not a.kind or not a.text:
        raise SystemExit("--kind and --text are required for record/status")
    led = ReviewLedger(a.ledger)
    if a.action == "record":
        led.record(a.kind, a.text, a.verdict, a.reviewer, a.note or "")
    out({"kind": a.kind, "text": a.text, "status": led.status(a.kind, a.text)})


def cmd_assets(a):
    am = AssetManager(Path(a.project) / "assets")
    if a.action == "register":
        out(am.register(a.id, a.kind, a.name, a.file))
    elif a.action == "list":
        out([{"id": x["id"], "kind": x["kind"], "approved": x["approved"], "versions": len(x["versions"])} for x in am.find()])
    elif a.action == "verify":
        issues = am.verify()
        out({"issues": issues})
        return 1 if issues else 0
    elif a.action == "approve":
        am.approve(a.id, a.actor)
        out({"approved": a.id})


def cmd_subtitles(a):
    m = json.loads(Path(a.script).read_text("utf-8"))
    r = subs_agent.build(m, age=a.age)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "subtitles.srt").write_text(r["srt"], "utf-8")
    (Path(a.out) / "subtitles.vtt").write_text(r["vtt"], "utf-8")
    out({"cues": len(r["cues"]), "issues": r["issues"]})


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio", description="Arabic Educational & Creative Studio 3.0")
    sp = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, *args, **kw):
        s = sp.add_parser(name, **kw)
        for flags, opts in args:
            s.add_argument(*flags if isinstance(flags, tuple) else (flags,), **opts)
        s.set_defaults(fn=fn)
        return s

    proj = (("project",), {})
    add("new", cmd_new, proj, (("--name",), {"required": True}))
    add("status", cmd_status, proj)
    add("step", cmd_step, proj, (("--until-blocked",), {"action": "store_true"}), (("--budget",), {"type": float, "default": None}))
    add("submit", cmd_submit, proj, (("stage",), {}), (("file",), {}), (("--actor",), {"default": "host"}))
    for d in ("approve", "reject", "modify", "regenerate", "rewind"):
        add(d, cmd_decide, proj, (("stage",), {}), (("--actor",), {"required": True}), (("--feedback",), {"default": ""}),
            (("--revision",), {"type": int, "default": None}), (("--file",), {"default": None}), (("--section",), {"default": None}))
    add("compare", cmd_compare, proj, (("stage",), {}), (("rev_a",), {"type": int}), (("rev_b",), {"type": int}))
    add("resume", cmd_resume, proj)
    add("verify", cmd_verify, proj)
    add("interview", cmd_interview, proj, (("action",), {"choices": ["next", "answer", "default", "summary", "confirm", "submit"]}),
        (("qid",), {"nargs": "?"}), (("value",), {"nargs": "?"}), (("--actor",), {"default": None}))
    add("styles", cmd_styles, (("action",), {"choices": ["list", "preview", "combine", "duplicate", "delete", "export", "import"]}),
        (("--store",), {"default": "styles"}), (("--id",), {}), (("--other",), {}), (("--new-id",), {}), (("--file",), {}), (("--force",), {"action": "store_true"}))
    add("providers", cmd_providers, (("action",), {"choices": ["list", "health"]}))
    add("lesson", cmd_lesson, (("letter",), {}), (("--out",), {"required": True}), (("--target",), {"type": float, "default": None}),
        (("--age",), {"default": "child"}), (("--lang",), {"default": "ar"}), (("--taught",), {"default": ""}), (("--ledger",), {"default": None}),
        (("--profile",), {"default": "preschool", "choices": ["preschool", "standard"]}),
        (("--theme",), {"default": "classroom", "choices": list(LP.THEMES)}))
    add("plan", cmd_plan, (("action",), {"choices": ["validate", "timeline", "voice", "stills", "render"]}), (("plan",), {}),
        (("--out",), {"default": None}), (("--formats",), {"default": None}), (("--audio",), {"default": None}),
        (("--no-captions",), {"action": "store_true"}), (("--concurrency",), {"type": int, "default": None}))
    add("review", cmd_review, (("action",), {"choices": ["record", "status", "export", "import"]}), (("file",), {"nargs": "?"}),
        (("--ledger",), {"default": None}), (("--kind",), {"default": None}), (("--out",), {"default": None}),
        (("--profile",), {"default": "preschool", "choices": ["preschool", "standard"]}),
        (("--text",), {"default": None}), (("--verdict",), {"default": "approved"}), (("--reviewer",), {"default": ""}), (("--note",), {"default": ""}))
    add("assets", cmd_assets, proj, (("action",), {"choices": ["register", "list", "verify", "approve"]}), (("--id",), {}), (("--kind",), {}),
        (("--name",), {}), (("--file",), {}), (("--actor",), {}))
    add("subtitles", cmd_subtitles, (("script",), {}), (("--out",), {"required": True}), (("--age",), {"default": "child"}))
    a = ap.parse_args(argv)
    if a.cmd in ("approve", "reject", "modify", "regenerate", "rewind"):
        a.cmd = a.cmd
    try:
        return a.fn(a) or 0
    except (StateError, ApprovalError, InterviewError, ValueError, KeyError) as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
