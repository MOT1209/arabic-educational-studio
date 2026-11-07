#!/usr/bin/env python3
"""بناء بأمر واحد، تزايدي: تحقق ← (إعادة توقيت من الصوت) ← تصيير المشاهد المتغيرة فقط ← دمج ← (صوت) ← فحص.

python build.py <مجلد الفيديو> <اسم الملف> [--audio مجلد] [--retime] [--music ملف] [--workers N] [--force] [--only scene_02 ...]
(--only يصيّر المشاهد المسماة فقط ويتوقف قبل الدمج — مناسب للمشهد التجريبي.)

- المشهد يُعاد تصييره فقط إن تغيّرت بصمة محتواه أو تغيّر القالب/المحرك أو فُقد ملفه (build/manifest.json).
- --retime يمدّد التوقيت ليتسع للصوت المسجَّل قبل التصيير (يتطلب --audio).
- يكتب build/build-report.md بما فُحص وما لم يُفحص."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from aes_common import scene_hash  # noqa: E402
from assemble import assemble  # noqa: E402
from render_scene import SceneError, render  # noqa: E402


def engine_sha():
    h = hashlib.sha256()
    for f in ("scene_template.html", "render_scene.py", "capabilities.json"):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:12]


def run(cmd):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out)
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir"); ap.add_argument("name")
    ap.add_argument("--audio"); ap.add_argument("--retime", action="store_true"); ap.add_argument("--music")
    ap.add_argument("--workers", type=int); ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    V = Path(a.video_dir).resolve(); script = V / "master-script.json"
    report = [f"# تقرير البناء — {a.name}", "", f"- الوقت: {time.strftime('%Y-%m-%d %H:%M')}"]

    if a.retime:
        if not a.audio:
            sys.exit("--retime يحتاج --audio")
        print("== إعادة التوقيت من الصوت"); run([SCRIPTS / "retime_from_audio.py", V, a.audio])

    print("== التحقق من السيناريو")
    code, out = run([SCRIPTS / "validate_script.py", script, "--update-hashes"])
    if code:
        sys.exit("توقف: صحّح أخطاء السيناريو أولاً")
    warns = [l for l in out.splitlines() if l.startswith("تحذير")]
    report.append(f"- التحقق: نجح، {len(warns)} تحذير")
    report += [f"  - {w}" for w in warns]

    doc = json.loads(script.read_text("utf-8"))
    mf_path = V / "build" / "manifest.json"; (V / "build").mkdir(exist_ok=True)
    mf = json.loads(mf_path.read_text("utf-8")) if mf_path.exists() else {}
    esha = engine_sha(); rendered, skipped = [], []
    for sc in doc["scenes"]:
        sid, h = sc["id"], scene_hash(sc)
        exp = V / "exports" / f"{sid}.mp4"
        stale = a.force or not exp.exists() or mf.get(sid) != {"hash": h, "engine": esha}
        if a.only is not None and a.only:
            stale = sid in a.only
        if not stale:
            skipped.append(sid); continue
        print(f"== تصيير {sid} ({sc['duration_seconds']}s)"); t0 = time.time()
        try:
            render(V, doc, sid, a.workers)
        except SceneError as e:
            sys.exit(f"توقف: {e}")
        mf[sid] = {"hash": h, "engine": esha}
        mf_path.write_text(json.dumps(mf, ensure_ascii=False, indent=2), "utf-8")
        rendered.append(f"{sid} ({time.time() - t0:.0f}s)")
    report.append("- صُيّرت: " + ("، ".join(rendered) or "لا شيء"))
    report.append("- لم تتغير (أُعيد استخدامها): " + ("، ".join(skipped) or "لا شيء"))

    if a.only:
        print("وضع --only: صُيّرت المشاهد المطلوبة فقط دون دمج:", ", ".join(str(V / "exports" / f"{x}.mp4") for x in a.only))
        return 0

    print("== الدمج"); out_path, total = assemble(V, a.name)
    final, srt = out_path, V / "subtitles" / f"{a.name}.srt"
    check_args = []
    if a.audio:
        print("== تركيب الصوت")
        cmd = [SCRIPTS / "mux_audio.py", V, a.name, a.audio] + (["--music", a.music] if a.music else [])
        code, out = run(cmd)
        final = V / "exports" / f"{a.name}-voiced.mp4"
        report.append("- الصوت: " + out.replace("\n", " | "))
    else:
        check_args = ["--allow-silent"]
        report.append("- الصوت: لم يُركَّب (فيديو صامت بترجمة فقط)")

    print("== الفحص التقني")
    code, out = run([SCRIPTS / "check_output.py", final, "--script", script, "--srt", srt, *check_args])
    report += ["- الفحص التقني:", "```", out, "```"]
    report += ["", "## لم يُفحص آلياً (يلزم فحص بشري)",
               "- صحة القاعدة والأمثلة والإعراب (مراجعة معلم).",
               "- النطق ومطابقته للنص (استماع).",
               "- موضع التشكيل في اللقطات (render_scene.py --shots ثم فحص بالعين).",
               "- سلاسة الحركة في التشغيل الفعلي."]
    (V / "build" / "build-report.md").write_text("\n".join(report) + "\n", "utf-8")
    print("النتيجة:", final, f"({total:.1f}s)", "| التقرير:", V / "build" / "build-report.md")
    return code


if __name__ == "__main__":
    sys.exit(main())
