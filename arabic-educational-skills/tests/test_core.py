import json

import pytest

from studio.core import workflow as W
from studio.core.approvals import Approvals, ApprovalError, diff
from studio.core.cost import BudgetExceeded, CostManager
from studio.core.orchestrator import AwaitingHost, FuncAgent, HostTask, Orchestrator
from studio.core.schema import validate
from studio.core.state import Project, StateError

PROJECT = {"project_type": "kids_education", "topic": "حرف الألف", "language": "ar", "audience": {"age_band": "child", "level": "beginner"},
           "visual_style": "classroom_2d_cartoon", "duration": {"mode": "fixed", "seconds": 300, "tolerance_pct": 10},
           "format": {"platform": "youtube", "aspect": "16:9"}, "workflow": "approval", "approved": True}


STORYBOARD = {"version": "1", "shots": [{"shot_number": 1, "scene_id": "scene_01", "shot_type": "wide", "camera_angle": "eye_level",
                                         "camera_movement": "static", "subject": "teacher", "background": "classroom", "duration_seconds": 5}]}


@pytest.fixture
def proj(tmp_path):
    return Project.create(tmp_path / "p", "تجربة")


def advance(p, upto, ap=None):
    """يمرّر المراحل السابقة لـ upto بمخرجات صالحة ويعتمد ما يحتاج اعتماداً."""
    ap = ap or Approvals(p)
    for sid in W.ORDER[:W.index(upto)]:
        art = PROJECT if sid == "interview" else ({"scenes": []} if sid == "script" else {"x": sid})
        if sid == "storyboard":
            art = STORYBOARD
        if sid == "script":
            art = json.load(open("references/example-master-script.json", encoding="utf-8"))
        p.submit(sid, art)
        if W.BY_ID[sid].approval:
            ap.approve(sid, "tester")


# ---------------- schema
def test_schema_rejects_unsupported_keyword():
    with pytest.raises(ValueError):
        validate({}, {"type": "object", "patternProperties": {}})


def test_schema_basic_violations():
    s = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer", "minimum": 1}, "b": {"enum": ["x"]}},
         "additionalProperties": False}
    assert validate({"a": 1}, s) == []
    assert len(validate({"a": 0, "b": "y", "c": 1}, s)) == 3
    assert validate({"a": True}, s)  # bool ليس integer


def test_schema_matches_jsonschema_when_available():
    js = pytest.importorskip("jsonschema")
    from studio.core.schema import load_schema
    s = load_schema("master-script.schema.json")
    d = json.load(open("references/example-master-script.json", encoding="utf-8"))
    assert validate(d, s) == [] and not list(js.Draft202012Validator(s).iter_errors(d))
    d["scenes"][0]["duration_seconds"] = -3
    assert bool(validate(d, s)) == bool(list(js.Draft202012Validator(s).iter_errors(d)))


# ---------------- state / workflow
def test_twelve_stages_and_required_approvals():
    assert len(W.ORDER) == 12
    needs = {s.id for s in W.STAGES if s.approval}
    assert {"creative_brief", "research", "script", "storyboard", "asset_planning", "final_export"} <= needs


def test_cannot_skip_stages(proj):
    with pytest.raises(StateError, match="upstream"):
        proj.submit("script", {})


def test_schema_enforced_on_submit(proj):
    with pytest.raises(StateError, match="violates"):
        proj.submit("interview", {"topic": "x"})
    assert proj.submit("interview", PROJECT) == 1


def test_approved_revision_never_overwritten(proj):
    advance(proj, "research")
    with pytest.raises(StateError, match="never overwritten"):
        proj.submit("creative_brief", {"y": 1})


# ---------------- approvals
def test_approve_requires_actor_and_latest_revision(proj):
    advance(proj, "creative_brief")
    proj.submit("creative_brief", {"v": 1})
    ap = Approvals(proj)
    with pytest.raises(ApprovalError, match="actor"):
        ap.approve("creative_brief", "")
    proj.set_status("creative_brief", "rejected")
    proj.submit("creative_brief", {"v": 2})
    with pytest.raises(ApprovalError, match="stale"):
        ap.approve("creative_brief", "tester", revision=1)
    rec = ap.approve("creative_brief", "tester", revision=2)
    assert rec["revision"] == 2 and rec["stage_id"] == "creative_brief" and rec["decision"] == "approve"
    assert {"project_id", "timestamp", "feedback"} <= set(rec)


def test_reject_needs_feedback_and_blocks_progress(proj):
    advance(proj, "creative_brief")
    proj.submit("creative_brief", {"v": 1})
    ap = Approvals(proj)
    with pytest.raises(ApprovalError):
        ap.reject("creative_brief", "t", "  ")
    ap.reject("creative_brief", "t", "ألوان غير مناسبة")
    assert proj.next_stage() == "creative_brief"
    with pytest.raises(StateError):
        proj.submit("research", {"x": 1})


def test_modify_and_compare_versions(proj):
    advance(proj, "creative_brief")
    proj.submit("creative_brief", {"palette": ["red"], "mood": "calm"})
    ap = Approvals(proj)
    ap.modify("creative_brief", "t", "غيّر الألوان", new_artifact={"palette": ["blue"], "mood": "calm"})
    assert proj.stage("creative_brief")["revision"] == 2
    assert ap.compare("creative_brief", 1, 2) == [{"path": "$.palette[0]", "a": "red", "b": "blue"}]


def test_regenerate_section_changes_only_that_section(proj):
    advance(proj, "creative_brief")
    proj.submit("creative_brief", {"a": {"x": 1}, "b": [1, 2, 3]})
    ap = Approvals(proj)
    ap.regenerate_section("creative_brief", "t", "b[1]", "غيّر العنصر")
    assert proj.status("creative_brief") == "needs_regeneration"
    ap.apply_section("creative_brief", "b[1]", 99)
    assert proj.artifact("creative_brief") == {"a": {"x": 1}, "b": [1, 99, 3]}
    with pytest.raises(ApprovalError):
        ap.regenerate_section("creative_brief", "t", "zzz", "x")


def test_rewind_invalidates_downstream_and_keeps_history(proj):
    advance(proj, "script")
    ap = Approvals(proj)
    ap.rewind("research", "t", "المصادر ناقصة")
    assert proj.status("research") == "invalidated" and proj.status("creative_brief") == "approved"
    assert proj.status("script") == "pending" or proj.status("script") == "invalidated"
    assert proj.next_stage() == "research"
    assert proj.revisions("research") == [1]          # التاريخ باقٍ للمقارنة
    assert ap.resume()["stage"] == "research"


def test_approval_log_is_chained_and_detects_tampering(proj):
    advance(proj, "script")
    ap = Approvals(proj)
    assert ap.verify() == [] and len(ap.records()) >= 2
    lines = ap.file.read_text("utf-8").splitlines()
    r = json.loads(lines[0])
    r["actor"] = "someone-else"
    lines[0] = json.dumps(r, ensure_ascii=False)
    ap.file.write_text("\n".join(lines) + "\n", "utf-8")
    assert any("altered" in i for i in ap.verify())


def test_resume_after_reopening_project(proj, tmp_path):
    advance(proj, "research")
    again = Project(proj.root)
    assert Approvals(again).resume()["stage"] == "research"


# ---------------- cost
def test_cost_budget_and_unknown_price(tmp_path):
    c = CostManager(tmp_path, budget_usd=1.0)
    c.charge("visual_production", "local", 10, 0.0)
    c.charge("visual_production", "mystery", 1, None)
    c.charge("visual_production", "x", 1, 0.9)
    with pytest.raises(BudgetExceeded):
        c.charge("visual_production", "x", 1, 0.2)
    t = c.total()
    assert t["usd_known"] == 0.9 and t["unknown_priced_calls"] == 1
    assert CostManager.estimate([{"provider": "a", "units": 2, "unit_cost_usd": 0.5}, {"provider": "b", "units": 1, "unit_cost_usd": None}]) \
        == {"usd_known": 1.0, "unknown_priced": ["b"], "items": 2}


# ---------------- orchestrator
def test_orchestrator_retries_with_feedback_then_succeeds(proj):
    seen = []

    def interview(ctx):
        seen.append(ctx["feedback"])
        return {"topic": "x"} if ctx["attempt"] == 1 else PROJECT

    o = Orchestrator(proj, {"interview": FuncAgent("i", interview)})
    o.step()
    assert proj.status("interview") == "done" and seen[0] is None and "violates" in seen[1]


def test_orchestrator_fails_after_max_retries(proj):
    o = Orchestrator(proj, {"interview": FuncAgent("i", lambda c: {"bad": 1})}, max_retries=1)
    o.step()
    assert proj.status("interview") == "failed"
    assert sum(1 for l in open(proj.root / "events.jsonl") if "invalid_output" in l) == 2


def test_host_task_roundtrip(proj):
    schema = {"type": "object", "required": ["topic"]}
    o = Orchestrator(proj, {"interview": HostTask("interviewer", "ask the user", schema)})
    r = o.step()
    assert r["outcome"] == "awaiting_host" and proj.status("interview") == "awaiting_output"
    task = json.load(open(r["task"], encoding="utf-8"))
    assert task["instructions"] == "ask the user" and task["output_schema"] == schema
    bad = o.provide_host_result("interview", {"nope": 1})
    assert bad["outcome"] == "invalid_output" and proj.status("interview") == "awaiting_output"
    ok = o.provide_host_result("interview", PROJECT)
    assert ok["outcome"] == "stored" and proj.status("interview") == "done"


def test_step_waits_for_approval(proj):
    advance(proj, "creative_brief")
    proj.submit("creative_brief", {"v": 1})
    assert Orchestrator(proj, {}).step()["outcome"] == "awaiting_approval"


def test_budget_blocks_expensive_stage(proj):
    advance(proj, "visual_production")
    proj.stage("asset_planning")
    # خطة معتمدة تقدّر 5$ والميزانية 1$ → التصيير محجوب
    p2 = Project(proj.root)
    with p2.lock():
        pass
    art = {"estimate": {"usd_known": 5.0}}
    p2.set_status("asset_planning", "needs_modification")
    p2.submit("asset_planning", art)
    Approvals(p2).approve("asset_planning", "t")
    o = Orchestrator(p2, {"visual_production": FuncAgent("r", lambda c: {"ok": 1})}, budget_usd=1.0)
    assert o.run_stage("visual_production")["outcome"] == "blocked"


def test_all_schema_files_are_valid_and_script_schema_in_sync():
    import pathlib
    root = pathlib.Path("schemas")
    names = {p.name for p in root.glob("*.json")}
    assert {"project", "script", "storyboard", "scene", "asset", "provider", "approval", "learning-lesson"} <= {n.split(".")[0] for n in names}
    for p in root.glob("*.schema.json"):
        s = json.loads(p.read_text("utf-8"))
        validate({}, s)   # يرمي ValueError إن استعمل المخطط كلمة مفتاحية غير مدعومة
    assert (root / "script.schema.json").read_text("utf-8") == open("references/master-script.schema.json", encoding="utf-8").read()


def test_approval_record_matches_schema(proj):
    advance(proj, "script")
    from studio.core.schema import load_schema
    s = load_schema("approval.schema.json")
    for r in Approvals(proj).records():
        assert validate(r, s) == [], r
