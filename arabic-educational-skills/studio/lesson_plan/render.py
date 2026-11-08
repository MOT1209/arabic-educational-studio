"""تصيير خطة الدرس بمحرك Remotion: يجهّز مجلداً عاماً (خطوط، صوت، صور)، ويحسب غلاف الفم من الصوت، ويستدعي node."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import plan as P

ENGINE = P.ROOT / "remotion"
FONTS = P.ROOT / "engine" / "fonts"


class RenderError(RuntimeError):
    pass


def chrome_path():
    if os.environ.get("AES_CHROME"):
        return os.environ["AES_CHROME"]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = p.chromium.executable_path
            return exe if Path(exe).exists() else None
    except Exception:
        return None


def ensure_engine():
    """يثبّت اعتماديات Node عند أول استعمال (npm install داخل remotion/)."""
    if (ENGINE / "node_modules" / "remotion").exists():
        return
    if not shutil.which("npm"):
        raise RenderError("Node.js/npm غير مثبت: المحرك يحتاج Node ≥ 18")
    r = subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=ENGINE, capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderError("فشل npm install:\n" + r.stderr[-2000:])


def mouth_envelope(props, fps=P.FPS):
    """غلاف شدة الصوت لكل إطار (0..1) من ملفات الصوت المسجّلة، ليتحرك فم الشخصية مع الكلام الحقيقي."""
    try:
        import numpy as np
    except ImportError:
        return None
    total = props["durationInFrames"]
    env = np.zeros(total, dtype=float)
    sr = 16000
    hop = sr // fps
    for a in props["audio"]:
        src = a["_abs"]
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                           capture_output=True)
        if r.returncode != 0:
            continue
        x = np.frombuffer(r.stdout, dtype=np.int16).astype(float) / 32768.0
        n = len(x) // hop
        if not n:
            continue
        rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
        peak = np.percentile(rms, 95) or 1.0
        v = np.clip(rms / peak, 0, 1)
        v[v < 0.12] = 0
        f0 = a["from"]
        m = min(n, total - f0)
        if m > 0:
            env[f0:f0 + m] = np.maximum(env[f0:f0 + m], v[:m])
    sm = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    return [round(float(v), 3) for v in sm]


def prepare(plan, fmt, work, audio_dir=None, captions=True):
    work = Path(work)
    pub = work / "public"
    if pub.exists():
        shutil.rmtree(pub)
    (pub / "fonts").mkdir(parents=True)
    for f in FONTS.glob("*.woff2"):
        shutil.copy(f, pub / "fonts" / f.name)
    props = P.render_props(plan, fmt, audio_dir, captions)
    if props["audio"]:
        (pub / "audio").mkdir()
        tl = P.timeline(plan, audio_dir)
        srcs = {Path(s["audio"]).name: s["audio"] for b in tl["blocks"] for s in b["segments"] if s.get("audio")}
        for a in props["audio"]:
            name = Path(a["src"]).name
            shutil.copy(srcs[name], pub / "audio" / name)
            a["_abs"] = srcs[name]
        props["mouth"] = mouth_envelope(props)
        for a in props["audio"]:
            a.pop("_abs", None)
    imgs = pub / "images"
    for b in props["blocks"]:
        if b.get("asset"):
            imgs.mkdir(exist_ok=True)
            src = Path(b["asset"])
            dst = imgs / f"{b['id']}{src.suffix.lower()}"
            shutil.copy(src, dst)
            b["asset_src"] = f"images/{dst.name}"
    pj = work / f"props-{fmt.replace(':', 'x')}.json"
    pj.write_text(json.dumps(props, ensure_ascii=False), "utf-8")
    return props, pj, pub


def run_node(props_json, out, pub, still=None, concurrency=None):
    ensure_engine()
    env = dict(os.environ)
    ch = chrome_path()
    if ch:
        env["AES_CHROME"] = ch
    cmd = ["node", str(ENGINE / "render.mjs"), str(props_json), str(out), str(pub)]
    if still is not None:
        cmd += ["--still", ",".join(map(str, still)) if isinstance(still, (list, tuple)) else str(still)]
    if concurrency:
        cmd += ["--concurrency", str(concurrency)]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderError("فشل التصيير:\n" + (r.stderr or r.stdout)[-3000:])
    return r.stdout


def write_sidecar(plan, fmt, video, srt, item):
    """يكتب `<name>-<fmt>.json` بجانب الفيديو (عقد C7) ويرفض بطاقة لا تجتاز التحقق."""
    path = Path(video).with_suffix(".json")
    doc = P.sidecar(plan, fmt, video, srt, item.get("seconds"), item.get("has_audio"), item.get("technical_check"))
    problems = P.check_sidecar(doc)
    if problems:
        raise RenderError("بطاقة التسليم غير صالحة:\n- " + "\n- ".join(problems))
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), "utf-8")
    return path


def render(plan, out_dir, formats=None, audio_dir=None, captions=True, stills_only=False, check=True, concurrency=None):
    """يصيّر كل صيغة إلى out_dir/<name>-<fmt>.mp4 + .srt. يعيد تقريراً صادقاً بما فُحص."""
    E, W = P.validate(plan)
    if E:
        raise RenderError("الخطة فيها أخطاء:\n- " + "\n- ".join(E))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / ".work"
    work.mkdir(exist_ok=True)
    report = {"warnings": W, "outputs": [], "missing_audio": P.timeline(plan, audio_dir)["missing_audio"] if audio_dir else []}
    name = plan.get("slug") or "lesson"
    for fmt in formats or plan.get("formats", ["16:9"]):
        props, pj, pub = prepare(plan, fmt, work, audio_dir, captions)
        tag = fmt.replace(":", "x")
        if stills_only:
            frames = [b["from"] + int(b["frames"] * 0.7) for b in props["blocks"]]
            run_node(pj, out_dir / f"{name}-{tag}.png", pub, still=frames)
            report["outputs"].append({"format": fmt, "stills": sorted(str(p) for p in out_dir.glob(f"{name}-{tag}_*.png"))})
            continue
        mp4 = out_dir / f"{name}-{tag}.mp4"
        run_node(pj, mp4, pub, concurrency=concurrency)
        (out_dir / f"{name}-{tag}.srt").write_text(P.srt(props), "utf-8")
        item = {"format": fmt, "video": str(mp4), "srt": str(out_dir / f"{name}-{tag}.srt"),
                "seconds": round(props["durationInFrames"] / props["fps"], 2), "has_audio": props["has_audio"]}
        if check:
            cmd = [sys.executable, str(P.ROOT / "scripts" / "check_output.py"), str(mp4), "--srt", item["srt"]]
            if not props["has_audio"]:
                cmd.append("--allow-silent")
            r = subprocess.run(cmd, capture_output=True, text=True)
            item["technical_check"] = "passed" if r.returncode == 0 else "failed"
            item["check_log"] = (r.stdout + r.stderr)[-1500:]
        item["sidecar"] = str(write_sidecar(plan, fmt, mp4, item["srt"], item))
        report["outputs"].append(item)
    return report
