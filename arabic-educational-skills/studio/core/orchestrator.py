"""المنسّق: كل تنسيق بين الوكلاء يمرّ من هنا. مدخلات/مخرجات مهيكلة تُتحقَّق بمخطط، إعادة محاولة مع تغذية راجعة،
حالة قابلة للاستئناف، تتبّع تكلفة، وسجل أحداث. الوكيل = كائن له run(ctx)->dict.
وكلاء المضيف (Claude) لا يُستدعون من الكود: HostTask يكتب ملف مهمة ويتوقف حتى يُقدَّم الناتج عبر provide_host_result."""
import json
import time
from pathlib import Path

from . import workflow as W
from .approvals import Approvals
from .cost import BudgetExceeded, CostManager
from .schema import validate
from .state import Project, StateError, atomic_write, now

RUNNABLE = {"pending", "invalidated", "rejected", "needs_modification", "needs_regeneration", "failed", "awaiting_output"}


class NonRetriable(Exception):
    """خطأ لا تفيد معه إعادة المحاولة (عملية مكلفة فشلت، مدخل خاطئ): تُحفَظ المرحلة failed فوراً."""


class AwaitingHost(Exception):
    def __init__(self, task_path):
        super().__init__(str(task_path))
        self.task_path = task_path


class Agent:
    """واجهة الوكيل. output_schema اختياري (dict) ويُفحص قبل الحفظ بالإضافة إلى مخطط المرحلة."""
    name = "agent"
    output_schema = None

    def run(self, ctx):  # pragma: no cover
        raise NotImplementedError


class FuncAgent(Agent):
    def __init__(self, name, fn, output_schema=None):
        self.name, self.fn, self.output_schema = name, fn, output_schema

    def run(self, ctx):
        return self.fn(ctx)


class HostTask(Agent):
    """مهمة إبداعية ينفذها Claude المضيف: تُكتب instructions + inputs + schema ثم يتوقف التنسيق."""
    def __init__(self, name, instructions, output_schema=None):
        self.name, self.instructions, self.output_schema = name, instructions, output_schema

    def run(self, ctx):
        proj, sid = ctx["project"], ctx["stage"]
        path = proj.root / "tasks" / "pending" / f"{sid}-attempt{ctx['revision_next']:03d}.json"
        atomic_write(path, json.dumps({"stage": sid, "agent": self.name, "instructions": self.instructions,
                                       "inputs": ctx["inputs"], "feedback": ctx.get("feedback"), "section": ctx.get("section"),
                                       "output_schema": self.output_schema, "stage_schema": W.BY_ID[sid].schema or None},
                                      ensure_ascii=False, indent=2))
        raise AwaitingHost(path)


class Orchestrator:
    def __init__(self, project: Project, agents=None, budget_usd=None, max_retries=2):
        self.p = project
        self.agents = agents or {}
        self.cost = CostManager(project.root, budget_usd)
        self.approvals = Approvals(project)
        self.max_retries = max_retries
        self.events = project.root / "events.jsonl"

    def _event(self, **kw):
        with open(self.events, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), **kw}, ensure_ascii=False) + "\n")

    def _inputs(self, sid):
        return {u: self.p.artifact(u) for u in W.upstream(sid) if self.p.stage(u)["revision"]}

    def run_stage(self, sid):
        st = W.BY_ID[sid]
        status = self.p.status(sid)
        if status not in RUNNABLE:
            return {"stage": sid, "outcome": "skipped", "reason": f"status is '{status}'"}
        blocked = [u for u in W.upstream(sid) if self.p.status(u) not in W.PASSING]
        if blocked:
            return {"stage": sid, "outcome": "blocked", "upstream_not_passed": blocked}
        if sid not in self.agents:
            return {"stage": sid, "outcome": "no_agent", "owner": st.owner}
        if st.expensive and sid != "asset_planning" and self.cost.budget is not None:
            plan = self.p.artifact("asset_planning") or {}
            est = plan.get("estimate", {}).get("usd_known", 0)
            if self.cost.would_exceed(est):
                return {"stage": sid, "outcome": "blocked", "reason": "approved plan estimate exceeds remaining budget"}
        agent, feedback, last_errors = self.agents[sid], self.p.stage(sid).get("feedback"), []
        section = self.p.stage(sid).get("section") if status == "needs_regeneration" else None
        for attempt in range(1, self.max_retries + 2):
            ctx = {"project": self.p, "stage": sid, "inputs": self._inputs(sid), "feedback": feedback, "section": section,
                   "attempt": attempt, "cost": self.cost, "revision_next": self.p.stage(sid)["revision"] + 1,
                   "previous": self.p.artifact(sid) if self.p.stage(sid)["revision"] else None}
            t0 = time.time()
            try:
                out = agent.run(ctx)
            except AwaitingHost as e:
                self.p.set_status(sid, "awaiting_output", task=str(e.task_path))
                self._event(stage=sid, attempt=attempt, outcome="awaiting_host", task=str(e.task_path))
                return {"stage": sid, "outcome": "awaiting_host", "task": str(e.task_path)}
            except NonRetriable as e:
                self.p.set_status(sid, "failed", error=str(e))
                self._event(stage=sid, attempt=attempt, outcome="failed_non_retriable", error=str(e)[:500])
                return {"stage": sid, "outcome": "failed", "error": str(e)}
            except BudgetExceeded as e:
                self.p.set_status(sid, "failed", error=str(e))
                self._event(stage=sid, attempt=attempt, outcome="budget_exceeded", error=str(e))
                return {"stage": sid, "outcome": "failed", "error": str(e)}
            except Exception as e:  # خطأ في الوكيل نفسه: لا نعيد المحاولة بصمت إلى ما لا نهاية
                last_errors = [f"{type(e).__name__}: {e}"]
                self._event(stage=sid, attempt=attempt, outcome="agent_error", error=last_errors[0])
                feedback = "previous attempt raised: " + last_errors[0]
                continue
            errs = validate(out, agent.output_schema) if agent.output_schema else []
            if not errs:
                try:
                    return self._store(sid, out, section, agent.name, attempt, time.time() - t0)
                except StateError as e:
                    errs = [str(e)]
            last_errors = errs
            feedback = "output rejected by validation; fix: " + " | ".join(errs[:6])
            self._event(stage=sid, attempt=attempt, outcome="invalid_output", errors=errs[:6])
        self.p.set_status(sid, "failed", error=" | ".join(last_errors[:6]))
        return {"stage": sid, "outcome": "failed", "errors": last_errors, "attempts": self.max_retries + 1}

    def _store(self, sid, out, section, author, attempt, seconds):
        if self.p.status(sid) == "needs_regeneration" and section:
            rev = self.approvals.apply_section(sid, section, out, author=author)
        else:
            rev = self.p.submit(sid, out, author=author)
        self._event(stage=sid, attempt=attempt, outcome="stored", revision=rev, seconds=round(seconds, 2))
        return {"stage": sid, "outcome": "stored", "revision": rev, "status": self.p.status(sid)}

    def provide_host_result(self, sid, artifact, author="host"):
        """يُستدعى بعد أن ينفذ Claude المهمة: يتحقق بالمخطط ويحفظ. فشل التحقق = لا حفظ ويعيد الأخطاء."""
        if self.p.status(sid) not in ("awaiting_output", "pending", "invalidated", "rejected", "needs_modification",
                                      "needs_regeneration", "failed"):
            raise StateError(f"stage '{sid}' is not waiting for output (status {self.p.status(sid)})")
        agent = self.agents.get(sid)
        errs = validate(artifact, agent.output_schema) if agent and agent.output_schema else []
        if errs:
            return {"stage": sid, "outcome": "invalid_output", "errors": errs}
        section = self.p.stage(sid).get("section") if self.p.status(sid) == "needs_regeneration" else None
        res = self._store(sid, artifact, section, author, 0, 0)
        for f in (self.p.root / "tasks" / "pending").glob(f"{sid}-*.json"):
            f.rename(self.p.root / "tasks" / "done" / f.name)
        return res

    def step(self):
        """يتقدم خطوة واحدة: يشغّل المرحلة التالية إن كانت قابلة للتشغيل، وإلا يشرح سبب الانتظار."""
        sid = self.p.next_stage()
        if sid is None:
            return {"outcome": "complete"}
        if self.p.status(sid) == "awaiting_approval":
            return {"stage": sid, "outcome": "awaiting_approval", "revision": self.p.stage(sid)["revision"]}
        return self.run_stage(sid)

    def run_until_blocked(self, max_steps=30):
        log = []
        for _ in range(max_steps):
            r = self.step()
            log.append(r)
            if r["outcome"] not in ("stored",) or (r.get("status") == "awaiting_approval"):
                break
        return log
