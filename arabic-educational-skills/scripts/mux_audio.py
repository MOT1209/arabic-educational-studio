#!/usr/bin/env python3
"""يركّب ملفات الصوت (باسم معرّف السطر) على الفيديو بحسب أزمنة السيناريو.
python mux_audio.py <مجلد الفيديو> <اسم الفيديو> <مجلد الصوت> [--music ملف] [--music-db -24]
→ exports/<اسم>-voiced.mp4
- الأسطر الناقصة تُتجاوز مع تنبيه؛ الأطول من وقتها تُبلَّغ (عالجها بـ retime_from_audio.py لا بالقص).
- إن وُجد voice-pack.csv في مجلد الصوت، يُنبَّه إلى كل سطر تغيّر نصه بعد تسجيله.
- الموسيقى (اختيارية) تُخفَض تلقائياً أثناء الكلام (ducking).
- يُطبَّع الصوت النهائي إلى -16 LUFS تقريباً (مناسب ليوتيوب والهواتف)."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aes_common import line_id, text_sha  # noqa: E402

EXTS = ("wav", "mp3", "m4a", "ogg", "flac")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())


def find_audio(A, lid):
    return next((A / f"{lid}.{e}" for e in EXTS if (A / f"{lid}.{e}").exists()), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir"); ap.add_argument("name"); ap.add_argument("audio_dir")
    ap.add_argument("--music"); ap.add_argument("--music-db", type=float, default=-24)
    a = ap.parse_args()
    V, A = Path(a.video_dir).resolve(), Path(a.audio_dir).resolve()
    doc = json.loads((V / "master-script.json").read_text("utf-8"))
    recorded = {}
    pack = A / "voice-pack.csv"
    if pack.exists():
        with open(pack, encoding="utf-8-sig") as f:
            recorded = {r["id"]: r.get("text_sha") for r in csv.DictReader(f)}
    inputs, filt, labels, off = [], [], [], 0
    missing, long_, stale = [], [], []
    for sc in doc["scenes"]:
        for i, d in enumerate(sc.get("dialogue", []), 1):
            lid = line_id(sc, i, d)
            text = d.get("tts_text") or d["text_diacritized"]
            if lid in recorded and recorded[lid] and recorded[lid] != text_sha(text):
                stale.append(lid)
            f = find_audio(A, lid)
            if not f:
                missing.append(lid); continue
            slot, L = d["end"] - d["start"], dur(f)
            if L > slot + 0.3:
                long_.append(f"{lid}: {L:.1f}s > {slot:.1f}s")
            n = len(labels); inputs += ["-i", str(f)]
            ms = int(round((off + d["start"]) * 1000))
            filt.append(f"[{n + 1}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{n}]")
            labels.append(f"[a{n}]")
        off += sc["duration_seconds"]
    if not labels:
        sys.exit("لا ملفات صوت مطابقة في " + str(A))
    filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad,atrim=0:{off}[v]")
    if a.music:
        k = len(labels) + 1; inputs += ["-stream_loop", "-1", "-i", a.music]
        filt.append(f"[v]asplit=2[vo][sc]")
        filt.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,volume={a.music_db}dB,atrim=0:{off}[mu]")
        filt.append("[mu][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck]")
        filt.append("[vo][duck]amix=inputs=2:normalize=0[mix]")
        last = "[mix]"
    else:
        last = "[v]"
    filt.append(f"{last}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[m]")
    src = V / "exports" / f"{a.name}.mp4"; out = V / "exports" / f"{a.name}-voiced.mp4"
    if not src.exists():
        print(f"خطأ: الفيديو المصدر غير موجود: {src}\nشغّل أولاً: python engine/build.py <مجلد الفيديو>")
        return 1
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), *inputs, "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(off), str(out)],
                   check=True)
    print("تم:", out, "| أسطر مركّبة:", len(labels))
    if missing:
        print("ناقصة:", ", ".join(missing))
    if long_:
        print("أطول من وقتها (شغّل retime_from_audio.py):", "; ".join(long_))
    if stale:
        print("تغيّر نصها بعد التسجيل (أعد تسجيلها):", ", ".join(stale))
    return 1 if (missing or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
