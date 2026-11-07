import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.core.state import Project
from studio.core.approvals import Approvals
from studio.core.orchestrator import Orchestrator
from studio.core import workflow as W
from studio.agents.interviewer import Interview
from studio.pipeline import default_agents
import shutil
R = Path(sys.argv[1]); shutil.rmtree(R, ignore_errors=True)
p = Project.create(R, "درس الألف")
iv = Interview(R / "interview.json")
given = {"topic": "تعليم حرف الألف للأطفال", "project_type": "kids_education", "letter": "ا", "duration": "custom", "duration_seconds": 300, "narration": "subtitles_only", "budget_usd": 0}
while (q := iv.next_question()):
    if q["id"] in given: iv.answer(q["id"], given[q["id"]])
    elif q.get("default") is not None: iv.accept_default(q["id"])
    else: print("NEEDS", q); sys.exit(1)
print(iv.summary()); proj = iv.confirm("hamad")
p.submit("interview", proj, author="hamad"); 
ap = Approvals(p)
o = Orchestrator(p, default_agents(p), budget_usd=0)
t=time.time()
for _ in range(40):
    r = o.run_until_blocked()
    print(json.dumps(r, ensure_ascii=False)[:400], round(time.time()-t), flush=True)
    st = ap.resume().get("stage")
    if any(x.get("outcome") == "failed" for x in r) or not st: break
    if p.status(st) == "awaiting_approval": ap.approve(st, "hamad", None, "e2e"); 
    else: break
print({s: p.status(s) for s in W.ORDER}); print(ap.verify())
ok = p.status("final_export") == "approved" and (R / "exports/final/video.mp4").exists() and not ap.verify()
sys.exit(0 if ok else 1)
