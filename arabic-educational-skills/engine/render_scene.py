#!/usr/bin/env python3
"""مصيِّر مشهد: python render_scene.py <مجلد الفيديو> <scene_id> [--shots t ...] [--render] [--workers N]
يقرأ master-script.json ويبني HTML من scene_template.html، ثم يلتقط لقطات اختبار أو يصيّر فيديو المشهد (صامتاً).
التصيير حتمي الزمن (renderAt(t))، لذا يُقسَّم على عدة متصفحات متوازية بأمان."""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPS = json.loads((HERE / "capabilities.json").read_text("utf-8"))


class SceneError(Exception):
    pass


def _image_src(doc, v):
    """asset بصيغة concept:<x> = لا صورة حقيقية بعد (يُرسم مكان محجوز موسوم)؛ مسار ملف موجود = يُعرض."""
    a = v.get("asset", "")
    if not a or a.startswith("concept:"):
        return None
    pth = Path(a)
    return pth.resolve().as_uri() if pth.exists() else None


def build_data(doc, sc):
    chars = CAPS["characters"]
    present = sc.get("characters", [])
    unknown = [c for c in present if c not in chars]
    if unknown:
        raise SceneError(f"{sc['id']}: شخصيات غير مرسومة في القالب: {', '.join(unknown)} (المتاح: {', '.join(chars)})")
    enter = sc.get("enter", {})
    inna_here = "inna" in present
    actors = []
    for c in present:
        slot = chars[c]["slot_with_inna"] if inna_here and "slot_with_inna" in chars[c] else chars[c]["slot"]
        x, top = slot
        actors.append({"id": c, "x": x, "top": top, "enter": enter.get(c, 0)})
    vis = sc.get("visuals", [])
    KID_TYPES = {"letter_card", "letter_highlight", "cue", "image"}
    is_kid_text = lambda v: v["type"] == "arabic_text" and (v.get("size") or v.get("role") or v.get("highlight_tokens"))  # noqa: E731
    kids = []
    for i, v in enumerate(sorted([v for v in vis if v["type"] in KID_TYPES or is_kid_text(v)], key=lambda v: v["start"])):
        base = {"id": i, "start": v["start"], "end": v["end"]}
        if v["type"] == "letter_card":
            kids.append({**base, "kind": "card", "letter": v["letter"], "name": v.get("name"), "forms": v.get("forms", {}),
                         "showForms": bool(v.get("show_forms"))})
        elif v["type"] == "cue":
            kids.append({**base, "kind": "cue", "text": v["text"]})
        elif v["type"] == "image":
            kids.append({**base, "kind": "img", "concept": v.get("note", ""), "src": _image_src(doc, v)})
        else:
            cls = " ".join(x for x in (v.get("size"), {"syllables": "small", "contrast_example": "contrast"}.get(v.get("role"), "")) if x)
            if any(k["kind"] == "img" and k["start"] < v["end"] and k["end"] > v["start"] for k in kids) or \
                    any(x["type"] == "image" and x["start"] < v["end"] and x["end"] > v["start"] for x in vis):
                cls += " side"
            kids.append({**base, "kind": "txt", "text": v["text_diacritized"], "cls": cls.strip(),
                         "hl": v.get("highlight_indices"), "tokens": v.get("highlight_tokens")})
    texts = sorted([v for v in vis if v["type"] == "arabic_text" and not is_kid_text(v)], key=lambda v: v["start"])
    board = [{"start": v["start"], "end": v["end"], "text": v["text_diacritized"], "status": v.get("status")} for v in texts]
    hls = [{"start": v["start"], "end": v["end"], "text": v["text_diacritized"], "role": v.get("color_role", ""), "tag": v.get("tag")}
           for v in vis if v["type"] == "highlight"]
    badges = [{"start": v["start"], "end": v["end"], "kind": v.get("kind", "right")} for v in vis if v["type"] == "badge"]
    quizzes = []
    for v in vis:
        if v["type"] != "quiz":
            continue
        reveal = v.get("reveal", v["end"] - 2)
        quizzes.append({"start": v["start"], "end": v["end"], "layout": v.get("layout", "rows"),
                        "prompt": v.get("prompt_diacritized"), "labels": v.get("labels", "letters"),
                        "options": [o["text_diacritized"] if isinstance(o, dict) else str(o) for o in v["options"]],
                        "answer": v["answer_index"], "countdown_from": v.get("countdown_from", reveal - 3), "reveal": reveal})
    names = {c["id"]: c["name"] for c in doc.get("characters", [])}
    return {"duration": sc["duration_seconds"], "fps": doc["output"]["fps"],
            "fadeOut": sc.get("transition") == "fade", "names": names, "actors": actors,
            "dialogue": [{"character": d["character"], "text": d.get("caption_text") or d["text_diacritized"], "start": d["start"],
                          "end": d["end"], "emotion": d.get("emotion")} for d in sc.get("dialogue", [])],
            "board": board, "highlights": hls, "badges": badges, "quizzes": quizzes, "kids": kids}


def srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def launch(pw):
    for exe in ("/usr/bin/google-chrome", None):
        try:
            kw = {"executable_path": exe} if exe and Path(exe).exists() else {}
            return pw.chromium.launch(args=["--no-sandbox", "--disable-gpu"], **kw)
        except Exception:
            if exe is None:
                raise


def write_html(V, doc, scene_id):
    sc = next((s for s in doc["scenes"] if s["id"] == scene_id), None)
    if sc is None:
        raise SceneError(f"لا يوجد مشهد {scene_id}")
    data = build_data(doc, sc)
    B = V / "build"; B.mkdir(exist_ok=True)
    html = B / f"{scene_id}.html"
    tpl = (HERE / "scene_template.html").read_text("utf-8")
    html.write_text(tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")), "utf-8")
    return html, data


def _render_range(args):
    html, frames_dir, fps, i0, i1 = args
    from playwright.sync_api import sync_playwright
    w, h = CAPS["resolution"]
    with sync_playwright() as pw:
        br = launch(pw)
        page = br.new_page(viewport={"width": w, "height": h})
        page.goto(Path(html).as_uri()); page.evaluate("window.ready")
        for i in range(i0, i1):
            page.evaluate(f"renderAt({i / fps})")
            page.screenshot(path=str(Path(frames_dir) / f"f{i:05d}.jpg"), type="jpeg", quality=90)
        br.close()
    return i1 - i0


def shots(V, doc, scene_id, times):
    html, _ = write_html(V, doc, scene_id)
    from playwright.sync_api import sync_playwright
    w, h = CAPS["resolution"]; out = []
    with sync_playwright() as pw:
        br = launch(pw)
        page = br.new_page(viewport={"width": w, "height": h})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(html.as_uri()); page.evaluate("window.ready")
        for t in times:
            page.evaluate(f"renderAt({t})")
            p = V / "build" / f"shot_{scene_id}_{t:05.1f}.png"; page.screenshot(path=str(p)); out.append(p)
        br.close()
    if errs:
        raise SceneError("أخطاء JavaScript في القالب: " + " | ".join(errs))
    return out


def render(V, doc, scene_id, workers=None):
    """يصيّر المشهد إلى exports/<id>.mp4 (فيديو + مسار صوت صامت) و subtitles/<id>.srt."""
    html, data = write_html(V, doc, scene_id)
    fps, dur = data["fps"], data["duration"]
    fr = V / "build" / f"frames_{scene_id}"; fr.mkdir(exist_ok=True)
    for o in fr.glob("*.jpg"):
        o.unlink()
    n = int(round(fps * dur))
    workers = max(1, min(workers or max(1, (os.cpu_count() or 2) - 1), 8, n))
    step = -(-n // workers)
    jobs = [(str(html), str(fr), fps, a, min(n, a + step)) for a in range(0, n, step)]
    if workers == 1:
        done = sum(_render_range(j) for j in jobs)
    else:
        with mp.get_context("spawn").Pool(len(jobs)) as pool:
            done = sum(pool.map(_render_range, jobs))
    if done != n or len(list(fr.glob("*.jpg"))) != n:
        raise SceneError(f"{scene_id}: صُيّر {done} من {n} إطاراً")
    (V / "subtitles").mkdir(exist_ok=True); (V / "exports").mkdir(exist_ok=True)
    srt = []
    for i, d in enumerate(data["dialogue"], 1):
        srt += [str(i), f"{srt_time(d['start'])} --> {srt_time(d['end'])}", d["text"], ""]
    (V / "subtitles" / f"{scene_id}.srt").write_text("\n".join(srt), "utf-8")
    out = V / "exports" / f"{scene_id}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(fr / "f%05d.jpg"),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", str(dur),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps),
                    "-c:a", "aac", "-shortest", str(out)], check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir"); ap.add_argument("scene")
    ap.add_argument("--shots", nargs="*", type=float); ap.add_argument("--render", action="store_true")
    ap.add_argument("--workers", type=int, help="عدد المتصفحات المتوازية (الافتراضي: عدد الأنوية - 1، حتى 8)")
    a = ap.parse_args()
    V = Path(a.video_dir).resolve()
    doc = json.loads((V / "master-script.json").read_text("utf-8"))
    try:
        for p in shots(V, doc, a.scene, a.shots or []):
            print(p)
        if a.render:
            print("video:", render(V, doc, a.scene, a.workers))
    except SceneError as e:
        print("خطأ:", e); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
