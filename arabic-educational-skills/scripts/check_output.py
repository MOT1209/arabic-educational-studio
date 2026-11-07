#!/usr/bin/env python3
"""يفحص فيديو الدرس النهائي بـ ffprobe، ويقارنه بالسيناريو وملف SRT.

الاستخدام:
    python check_output.py exports/lesson.mp4 [--script master-script.json] [--srt subtitles/lesson.srt]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def probe(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", video],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "ffprobe فشل")
    return json.loads(out.stdout)


def loudness(video):
    """يعيد (mean_db, max_db) لمسار الصوت عبر volumedetect، أو None."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-map", "0:a:0", "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", r.stderr); x = re.search(r"max_volume: (-?[\d.]+|-inf) dB", r.stderr)
    if not (m and x):
        return None
    f = lambda s: float("-inf") if s == "-inf" else float(s)
    return f(m.group(1)), f(x.group(1))


def black_ratio(video, duration):
    """نسبة زمن الإطارات السوداء (مشاهد ناقصة أو تلاشٍ طويل)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vf", "blackdetect=d=0.5:pic_th=0.97",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    total = sum(float(d) for d in re.findall(r"black_duration:([\d.]+)", r.stderr))
    return total / duration if duration else 0


def parse_srt_time(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def check_srt(path, duration):
    problems = []
    text = Path(path).read_text(encoding="utf-8")
    cues = re.findall(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", text)
    if not cues:
        return ["SRT لا يحتوي أي مقاطع زمنية صالحة"]
    prev_end = 0
    for i, (a, b) in enumerate(cues, 1):
        s, e = parse_srt_time(a), parse_srt_time(b)
        if e <= s:
            problems.append(f"SRT مقطع {i}: النهاية قبل البداية")
        if s < prev_end - 1e-3:
            problems.append(f"SRT مقطع {i}: يتداخل مع السابق")
        prev_end = max(prev_end, e)
    if prev_end > duration + 0.5:
        problems.append(f"SRT ينتهي ({prev_end:.1f}s) بعد نهاية الفيديو ({duration:.1f}s)")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--script")
    ap.add_argument("--srt")
    ap.add_argument("--tolerance", type=float, default=0.03)
    ap.add_argument("--allow-silent", action="store_true", help="فيديو بلا كلام مقصود (ترجمة فقط)")
    args = ap.parse_args()

    problems, notes = [], []
    try:
        info = probe(args.video)
    except FileNotFoundError:
        print("ffprobe غير مثبت؛ لا يمكن فحص الملف")
        return 2
    except RuntimeError as e:
        print("خطأ:", e)
        return 1

    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(info["format"].get("duration", 0))

    if not v:
        problems.append("لا يوجد مسار فيديو")
    else:
        notes.append(f"الدقة {v.get('width')}x{v.get('height')} ، الترميز {v.get('codec_name')}")
        num, _, den = v.get("avg_frame_rate", "0/1").partition("/")
        try:
            fps = float(num) / float(den or 1)
            notes.append(f"معدل الإطارات {fps:.2f}")
        except ZeroDivisionError:
            pass
    if not a:
        problems.append("لا يوجد مسار صوت")
    else:
        notes.append(f"الصوت {a.get('codec_name')} ، {a.get('sample_rate')} Hz")
        lv = loudness(args.video)
        if lv:
            notes.append(f"مستوى الصوت: متوسط {lv[0]} dB، أقصى {lv[1]} dB")
            if lv[1] < -50:
                (notes if args.allow_silent else problems).append(
                    "مسار الصوت صامت فعلياً (لا كلام مركّب)" + (" — مقبول: ترجمة فقط" if args.allow_silent else ""))
            elif lv[1] > -0.5:
                problems.append("الصوت يبلغ 0 dB تقريباً (احتمال تشوّه/قص)")
    notes.append(f"المدة {duration:.2f} ثانية")
    if v and duration:
        br = black_ratio(args.video, duration)
        if br > 0.05:
            problems.append(f"إطارات سوداء {br*100:.0f}% من الفيديو (مشهد ناقص أو تلاشٍ طويل؟)")

    if args.script:
        doc = json.loads(Path(args.script).read_text(encoding="utf-8"))
        planned = sum(s.get("duration_seconds", 0) for s in doc.get("scenes", []))
        diff = abs(duration - planned) / planned if planned else 0
        notes.append(f"المدة المخططة {planned:.2f}s")
        if diff > args.tolerance:
            problems.append(f"المدة الفعلية تختلف عن المخططة بنسبة {diff*100:.1f}% (السماحية {args.tolerance*100:.0f}%)")
        out = doc.get("output", {})
        if v and out.get("width") and (v.get("width"), v.get("height")) != (out["width"], out["height"]):
            problems.append(f"الدقة {v.get('width')}x{v.get('height')} لا تطابق المخطط {out['width']}x{out['height']}")

    if args.srt:
        problems += check_srt(args.srt, duration)

    for n in notes:
        print("•", n)
    for p in problems:
        print("مشكلة:", p)
    print("اجتاز الفحص التقني" if not problems else f"{len(problems)} مشكلة")
    print("ملاحظة: هذا فحص تقني فقط؛ التشكيل والنطق والإعراب يُفحصون باللقطات والاستماع.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
