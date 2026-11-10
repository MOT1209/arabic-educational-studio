#!/usr/bin/env python3
"""حزمة نشر يوتيوب من فيديو مصيَّر بصوته: مقدمة/خاتمة، صوت −14 LUFS، SRT مُزاح، وصف بفصول، صورة مصغّرة، ومقاطع عمودية.

python scripts/publish_youtube.py <video.mp4> <publish.json> --out <dir> [--srt subtitles.srt] [--lufs -14] [--skip-thumbnail] [--skip-shorts]

publish.json (كل ما عدا title اختياري):
{
  "title": "إنَّ وأخواتها للأطفال | مدرستي العربية",
  "description": "نص الوصف...",
  "tags": ["نحو", "إن وأخواتها"],
  "intro": "intro.mp4", "outro": "outro.mp4",                 // مسارات نسبة إلى ملف publish.json
  "intro_chapter": "المقدمة",
  "chapters": [{"t": 0, "title": "الخطأ الشائع"}, {"t": 35, "title": "القاعدة"}, ...],   // ثوانٍ في الفيديو الأصلي
  "shorts": [{"name": "hook", "start": 5, "end": 40}],
  "thumbnail": {"title": "إنَّ وأخواتها", "subtitle": "للأطفال", "frame_at": 20, "image": null}
}
المخرجات في --out: youtube.mp4 · subtitles.srt · title.txt · description.txt · tags.txt · thumbnail.jpg · shorts/*.mp4 · publish-report.md

ما يفحصه: قواعد فصول يوتيوب (تبدأ 0:00، ثلاثة فأكثر، ≥10ث بين كل فصلين)، حدود العنوان والوصف والوسوم، مدة المقاطع،
الصوت الناتج بقياس فعلي. ما لا يفحصه: سماع الصوت، مشاهدة الحركة، شكل الصورة المصغّرة (انظر إليها بنفسك)، ترجمة المقاطع العمودية (لا تُحرَق).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_BOLD = SKILL_DIR / "engine" / "fonts" / "noto-sans-arabic-arabic-700-normal.woff2"
W, H, FPS = 1920, 1080, 30


class PublishError(Exception):
    pass


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        raise PublishError(f"ffmpeg/ffprobe فشل ({r.returncode}): {' '.join(map(str, cmd[:3]))}...\n{r.stderr[-800:]}")
    return r


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", path])
    d = json.loads(r.stdout)
    st = d.get("streams", [])
    v = next((s for s in st if s["codec_type"] == "video"), None)
    return {"duration": float(d["format"]["duration"]), "has_audio": any(s["codec_type"] == "audio" for s in st),
            "width": v and v.get("width"), "height": v and v.get("height")}


def fmt_ts(sec):
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------- التحقق من البيانات الوصفية ----------
def validate_meta(meta, dur_main, intro_dur):
    errors, warns = [], []
    title = meta.get("title", "")
    if not title.strip():
        errors.append("title مطلوب")
    if len(title) > 100:
        errors.append(f"العنوان {len(title)} حرفاً (الحد 100)")
    elif len(title) > 70:
        warns.append(f"العنوان {len(title)} حرفاً: يُقصّ في نتائج البحث بعد نحو 70")
    if len(meta.get("description", "")) > 4500:
        errors.append("الوصف يقترب من حد 5000 حرف")
    if "<" in title or ">" in title:
        errors.append("العنوان لا يقبل < أو >")
    tags = meta.get("tags", [])
    if sum(len(t) + 1 for t in tags) > 500:
        errors.append("مجموع الوسوم يتجاوز 500 حرف")
    ch = meta.get("chapters", [])
    if ch:
        ts = [c["t"] for c in ch]
        if ts != sorted(ts) or len(set(ts)) != len(ts):
            errors.append("الفصول يجب أن تكون بترتيب زمني تصاعدي بلا تكرار")
        if ts and ts[-1] >= dur_main:
            errors.append(f"فصل بعد نهاية الفيديو ({ts[-1]}ث ≥ {dur_main:.1f}ث)")
        if len(ch) < 3:
            warns.append("يوتيوب لا يفعّل الفصول بأقل من ثلاثة")
        shifted = [t + intro_dur for t in ts]
        if intro_dur == 0 and shifted and shifted[0] != 0:
            errors.append("أول فصل يجب أن يبدأ عند 0:00")
        gaps = [b - a for a, b in zip(shifted, shifted[1:])]
        if any(g < 10 for g in gaps):
            errors.append("كل فصل ≥ 10 ثوانٍ")
    for s in meta.get("shorts", []):
        ln = s["end"] - s["start"]
        if not (0 <= s["start"] < s["end"] <= dur_main + 0.01):
            errors.append(f"مقطع {s.get('name')}: حدود غير صالحة")
        elif ln > 180:
            errors.append(f"مقطع {s.get('name')} {ln:.0f}ث: أطول من 180ث")
        elif ln > 60:
            warns.append(f"مقطع {s.get('name')} {ln:.0f}ث: فوق دقيقة (تيك توك/شورتس الأفضل ≤ 60)")
    return errors, warns


# ---------- SRT ----------
SRT_T = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{3})")


def _to_s(m):
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def _from_s(x):
    x = max(0, x)
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def shift_srt(text, offset):
    n = 0

    def rep(line):
        nonlocal n
        if "-->" not in line:
            return line
        a, b = line.split("-->")
        ma, mb = SRT_T.search(a), SRT_T.search(b)
        if not (ma and mb):
            return line
        n += 1
        return f"{_from_s(_to_s(ma) + offset)} --> {_from_s(_to_s(mb) + offset)}"
    return "\n".join(rep(l) for l in text.replace("\r\n", "\n").split("\n")), n


# ---------- الفيديو الرئيسي ----------
def _chains(inputs):
    """inputs: [(path, info)] ← (سلاسل الفيديو، سلاسل الصوت) بمعايير موحّدة 1080p30 وصوت 48k ستيريو."""
    vch, ach = [], []
    for i, (_, info) in enumerate(inputs):
        vch.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p[v{i}]")
        if info["has_audio"]:
            ach.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
        else:
            ach.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{info['duration']:.3f},asetpts=N/SR/TB[a{i}]")
    return vch, ach


def measure_loudness(inputs, lufs):
    _, ach = _chains(inputs)
    n = len(inputs)
    fc = ";".join(ach) + ";" + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[ac];[ac]loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json[o]"
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    for p, _ in inputs:
        cmd += ["-i", p]
    r = run(cmd + ["-filter_complex", fc, "-map", "[o]", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        raise PublishError("تعذّر قراءة قياس الصوت (loudnorm)")
    return json.loads(m.group(0))


def build_main(inputs, out, lufs):
    mz = measure_loudness(inputs, lufs)
    vch, ach = _chains(inputs)
    n = len(inputs)
    fc = ";".join(vch + ach) + ";" + "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][ac]"
    fc += (f";[ac]loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={mz['input_i']}:measured_TP={mz['input_tp']}:"
           f"measured_LRA={mz['input_lra']}:measured_thresh={mz['input_thresh']}:offset={mz['target_offset']}:linear=true[a]")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y"]
    for p, _ in inputs:
        cmd += ["-i", p]
    run(cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
               "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    return mz


def measure_output(path):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = r.stderr.split("Summary:")[-1]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(i.group(1)) if i else None), (float(p.group(1)) if p else None)


# ---------- مقاطع عمودية ----------
def build_short(src, out, start, end, lufs):
    ln = end - start
    fc = (f"[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5[bg];"
          f"[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS},format=yuv420p[v];"
          f"[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I={lufs}:TP=-1.5:LRA=11,"
          f"afade=t=in:d=0.15,afade=t=out:st={max(0, ln - 0.3):.2f}:d=0.3[a]")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{start}", "-t", f"{ln}", "-i", src, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", out])


# ---------- صورة مصغّرة ----------
def build_thumbnail(src_video, out, spec, workdir, intro_dur=0.0):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "playwright غير مثبّت: تخطّيت الصورة المصغّرة"
    bg = spec.get("image")
    if not bg:
        bg = workdir / "thumb-frame.jpg"
        run(["ffmpeg", "-hide_banner", "-y", "-ss", str(spec.get("frame_at", 5)), "-i", src_video, "-frames:v", "1", "-q:v", "2", bg])
    esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<!doctype html><html dir="rtl" lang="ar"><meta charset="utf-8"><style>
@font-face{{font-family:N;font-weight:700;src:url('{FONT_BOLD.as_uri()}')}}
html,body{{margin:0;width:1280px;height:720px;overflow:hidden;background:#000}}
.clip{{position:absolute;inset:0;overflow:hidden}}
.bg{{position:absolute;inset:-80px;background:url('{Path(bg).resolve().as_uri()}') center/cover;filter:blur(14px) brightness(.6) saturate(1.2)}}
.shade{{position:absolute;inset:0;background:linear-gradient(to left,rgba(0,0,0,.65),rgba(0,0,0,0) 70%)}}
.t{{position:absolute;right:70px;top:50%;transform:translateY(-50%);width:1000px;text-align:right;font:700 150px/1.25 N,sans-serif;color:#fff;text-shadow:0 6px 24px rgba(0,0,0,.8)}}
.s{{display:block;margin-top:26px;font:700 70px/1.3 N,sans-serif;color:#ffd54a}}
</style><div class="clip"><div class="bg"></div></div><div class="shade"></div><div class="t">{esc(spec.get('title'))}<span class="s">{esc(spec.get('subtitle'))}</span></div></html>"""
    hp = workdir / "thumb.html"
    hp.write_text(html, "utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(hp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(out), type="jpeg", quality=90)
        b.close()
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("meta")
    ap.add_argument("--out", required=True); ap.add_argument("--srt")
    ap.add_argument("--lufs", type=float, default=-14)
    ap.add_argument("--skip-thumbnail", action="store_true"); ap.add_argument("--skip-shorts", action="store_true")
    a = ap.parse_args(argv)

    video = Path(a.video).resolve()
    mp = Path(a.meta).resolve()
    meta = json.loads(mp.read_text("utf-8"))
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "shorts").mkdir(exist_ok=True)

    main_info = probe(video)
    if not main_info["has_audio"]:
        raise PublishError("الفيديو بلا صوت: ركّب الصوت أولاً (mux_audio.py)")
    inputs = []
    intro_dur = 0.0
    for key in ("intro",):
        if meta.get(key):
            p = (mp.parent / meta[key]).resolve()
            if not p.is_file():
                raise PublishError(f"{key} غير موجود: {p}")
            info = probe(p); inputs.append((p, info)); intro_dur = info["duration"]
    inputs.append((video, main_info))
    if meta.get("outro"):
        p = (mp.parent / meta["outro"]).resolve()
        if not p.is_file():
            raise PublishError(f"outro غير موجود: {p}")
        inputs.append((p, probe(p)))

    errors, warns = validate_meta(meta, main_info["duration"], intro_dur)
    if errors:
        print("أخطاء في publish.json:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 2

    report = {"checked": [], "not_checked": ["الاستماع للصوت", "مشاهدة الحركة", "شكل الصورة المصغّرة", "ترجمة المقاطع العمودية (لا تُحرَق)"], "warnings": warns}

    # الفيديو
    yt = out / "youtube.mp4"
    mz = build_main(inputs, yt, a.lufs)
    li, tp = measure_output(yt)
    final = probe(yt)
    expect = sum(i["duration"] for _, i in inputs)
    report["checked"].append(f"المدة {final['duration']:.1f}ث (المتوقع {expect:.1f}ث)، الدقة {final['width']}×{final['height']}")
    if abs(final["duration"] - expect) > 1.0:
        warns.append(f"المدة تختلف عن المجموع بأكثر من ثانية ({final['duration']:.1f} مقابل {expect:.1f})")
    report["checked"].append(f"الصوت المقيس: {li} LUFS، قمة {tp} dBFS (الهدف {a.lufs})")
    if li is None or abs(li - a.lufs) > 1.5:
        warns.append(f"الصوت المقيس {li} بعيد عن الهدف {a.lufs}")
    if tp is not None and tp > -1.0:
        warns.append(f"قمة الصوت {tp} dBFS قريبة من القص")

    # ترجمة
    srt_path = Path(a.srt) if a.srt else None
    if srt_path is None:
        cand = video.parent / "subtitles.srt"
        srt_path = cand if cand.exists() else None
    if srt_path and srt_path.exists():
        txt, n = shift_srt(srt_path.read_text("utf-8"), intro_dur)
        (out / "subtitles.srt").write_text(txt, "utf-8")
        last = max((_to_s(m) for m in SRT_T.finditer(txt)), default=0)
        report["checked"].append(f"SRT: {n} مقطعاً، أُزيح {intro_dur:.1f}ث، آخر زمن {last:.1f}ث")
        if last > final["duration"] + 0.5:
            warns.append("زمن في SRT يتجاوز نهاية الفيديو")
    else:
        warns.append("لا ملف SRT (مرّر --srt)")

    # نصوص
    ch = [(c["t"] + intro_dur, c["title"]) for c in meta.get("chapters", [])]
    if ch and intro_dur > 0 and ch[0][0] > 0:
        ch.insert(0, (0, meta.get("intro_chapter", "المقدمة")))
    desc = meta.get("description", "").rstrip()
    if ch:
        desc += "\n\n" + "\n".join(f"{fmt_ts(t)} {title}" for t, title in ch)
    (out / "description.txt").write_text(desc + "\n", "utf-8")
    (out / "title.txt").write_text(meta["title"] + "\n", "utf-8")
    (out / "tags.txt").write_text(", ".join(meta.get("tags", [])) + "\n", "utf-8")
    report["checked"].append(f"الفصول: {len(ch)}، العنوان {len(meta['title'])} حرفاً، الوصف {len(desc)} حرفاً")

    # صورة مصغّرة
    if meta.get("thumbnail") and not a.skip_thumbnail:
        tmp = out / ".tmp"; tmp.mkdir(exist_ok=True)
        msg = build_thumbnail(video, out / "thumbnail.jpg", meta["thumbnail"], tmp)
        if msg:
            warns.append(msg)
        else:
            sz = (out / "thumbnail.jpg").stat().st_size
            report["checked"].append(f"الصورة المصغّرة 1280×720، {sz // 1024}KB")
            if sz > 2_000_000:
                warns.append("الصورة المصغّرة فوق 2MB (حد يوتيوب)")

    # مقاطع عمودية
    shorts = []
    if meta.get("shorts") and not a.skip_shorts:
        for s in meta["shorts"]:
            name = re.sub(r"[^\w\-]+", "_", s.get("name", f"short{len(shorts) + 1}"))
            p = out / "shorts" / f"{name}.mp4"
            build_short(str(video), str(p), s["start"], s["end"], a.lufs)
            i = probe(p)
            shorts.append(f"{name}: {i['duration']:.1f}ث {i['width']}×{i['height']}")
        report["checked"].append("مقاطع عمودية: " + "؛ ".join(shorts))

    lines = ["# تقرير النشر", "", "## فُحص", *[f"- {c}" for c in report["checked"]], "", "## تحذيرات",
             *([f"- {w}" for w in warns] or ["- لا شيء"]), "", "## لم يُفحص", *[f"- {c}" for c in report["not_checked"]]]
    (out / "publish-report.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PublishError as e:
        print(f"خطأ: {e}", file=sys.stderr)
        sys.exit(1)
