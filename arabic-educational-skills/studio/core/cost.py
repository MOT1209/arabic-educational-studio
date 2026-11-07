"""إدارة التكلفة: ميزانية، سجل إنفاق إلحاقي، وتقدير خطة. لا يخترع أسعاراً: سعر مجهول يُسجَّل unknown ويُحتسب منفصلاً."""
import json
from pathlib import Path

from .state import now


class BudgetExceeded(Exception):
    pass


class CostManager:
    def __init__(self, project_root, budget_usd=None):
        self.file = Path(project_root) / "cost.jsonl"
        self.budget = budget_usd

    def entries(self):
        if not self.file.exists():
            return []
        return [json.loads(l) for l in self.file.read_text("utf-8").splitlines() if l.strip()]

    def total(self):
        known = sum(e["usd"] for e in self.entries() if e["usd"] is not None)
        unknown = sum(1 for e in self.entries() if e["usd"] is None)
        return {"usd_known": round(known, 4), "unknown_priced_calls": unknown, "budget_usd": self.budget,
                "remaining_usd": None if self.budget is None else round(self.budget - known, 4)}

    def would_exceed(self, usd):
        return self.budget is not None and self.total()["usd_known"] + (usd or 0) > self.budget

    def charge(self, stage, provider, units, usd, note=""):
        """usd=None يعني «السعر غير معروف». يرمي BudgetExceeded قبل الكتابة إن تجاوز الإنفاق الميزانية."""
        if usd is not None and usd < 0:
            raise ValueError("usd must be >= 0")
        if self.would_exceed(usd):
            raise BudgetExceeded(f"charge {usd} USD would exceed budget {self.budget} (spent {self.total()['usd_known']})")
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "stage": stage, "provider": provider, "units": units, "usd": usd, "note": note},
                               ensure_ascii=False) + "\n")

    @staticmethod
    def estimate(items):
        """items: [{provider, units, unit_cost_usd|None}] → مجموع معروف + عدد البنود مجهولة السعر."""
        known = sum(i["units"] * i["unit_cost_usd"] for i in items if i.get("unit_cost_usd") is not None)
        unknown = [i["provider"] for i in items if i.get("unit_cost_usd") is None]
        return {"usd_known": round(known, 4), "unknown_priced": unknown, "items": len(items)}
