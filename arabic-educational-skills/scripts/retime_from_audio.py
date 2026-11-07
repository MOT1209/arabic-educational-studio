#!/usr/bin/env python3
"""يمدّد توقيت السيناريو ليتسع للصوت المسجَّل فعلاً (بدل قص الصوت أو تسريعه).
python retime_from_audio.py <مجلد الفيديو> <مجلد الصوت> [--pad 0.25] [--dry-run]

لكل سطر صوته أطول من وقته: يُمدَّد السطر، ويُزاح كل ما يبدأ بعد نهايته في المشهد نفسه (حوار، مرئيات،
عدّاد السؤال، كشف الإجابة، دخول الشخصيات)، وتُمدَّد المرئيات الممتدة عبره، وتزيد مدة المشهد.
لا يُقصّر أي توقيت. يحفظ نسخة احتياطية master-script.before-retime.json ثم يحدّث البصمات."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aes_common import line_id, write_json  # noqa: E402
from mux_audio import dur, find_audio  # noqa: E402

EPS = 1e-6


def shift_scene(sc, after, delta):
    """يزيح كل زمن ≥ after بمقدار delta داخل المشهد."""
    def mv(x):
        return round(x + delta, 3) if x >= after - EPS else x
    for d in sc.get("dialogue", []):
        d["start"], d["end"] = mv(d["start"]), mv(d["end"])
    for v in sc.get("visuals", []):
        v["start"], v["end"] = mv(v["start"]), mv(v["end"])
        for k in ("countdown_from", "reveal"):
            if k in v:
                v[k] = mv(v[k])
    for c, t in list(sc.get("enter", {}).items()):
        sc["enter"][c] = mv(t)
    sc["duration_seconds"] = round(sc["duration_seconds"] + delta, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir"); ap.add_argument("audio_dir")
    ap.add_argument("--pad", type=float, default=0.25, help="فراغ بعد كل سطر (ث)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    V, A = Path(a.video_dir).resolve(), Path(a.audio_dir).resolve()
    sp = V / "master-script.json"
    doc = json.loads(sp.read_text("utf-8"))
    report, total = [], 0.0
    for sc in doc["scenes"]:
        lines = [(line_id(sc, i, d), d) for i, d in enumerate(sc.get("dialogue", []), 1)]
        for lid, d in sorted(lines, key=lambda x: x[1]["start"]):
            f = find_audio(A, lid)
            if not f:
                continue
            need = dur(f) + a.pad
            slot = d["end"] - d["start"]
            if need > slot + EPS:
                delta = round(need - slot, 3)
                old_end = d["end"]
                shift_scene(sc, old_end, delta)  # يزيح ما بعد السطر (ومنه نهايته هو)
                report.append(f"{lid}: +{delta:.2f}s")
                total += delta
    if not report:
        print("كل الأسطر تتسع لصوتها؛ لا تغيير"); return 0
    print("\n".join(report)); print(f"زيادة كلية: {total:.2f}s")
    if a.dry_run:
        print("(تشغيل تجريبي؛ لم يُحفظ شيء)"); return 0
    shutil.copy2(sp, V / "master-script.before-retime.json")
    write_json(sp, doc)
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "validate_script.py"), str(sp), "--update-hashes"])
    print("حُفظ؛ أعد إنتاج المشاهد المتغيرة (build.py يفعل ذلك تلقائياً)")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
