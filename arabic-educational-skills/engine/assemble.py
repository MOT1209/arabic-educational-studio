#!/usr/bin/env python3
"""python assemble.py <مجلد الفيديو> <اسم الملف> : يدمج exports/scene_XX.mp4 بالترتيب ويبني SRT كاملاً بإزاحات تراكمية."""
import json
import subprocess
import sys
from pathlib import Path

from render_scene import srt_time


def assemble(V, name):
    V = Path(V).resolve()
    doc = json.loads((V / "master-script.json").read_text("utf-8"))
    (V / "build").mkdir(exist_ok=True); (V / "subtitles").mkdir(exist_ok=True)
    lst = V / "build" / "concat.txt"
    srt, off, n, lines = [], 0.0, 1, []
    for sc in doc["scenes"]:
        f = V / "exports" / f"{sc['id']}.mp4"
        if not f.exists():
            raise FileNotFoundError(f"مشهد غير مصيَّر: {f}")
        lines.append("file '" + f.as_posix().replace("'", "'\\''") + "'")  # هروب الفاصلة العليا بصيغة concat demuxer
        for d in sc.get("dialogue", []):
            srt += [str(n), f"{srt_time(off + d['start'])} --> {srt_time(off + d['end'])}", d.get("caption_text") or d["text_diacritized"], ""]
            n += 1
        off += sc["duration_seconds"]
    lst.write_text("\n".join(lines) + "\n", "utf-8")
    (V / "subtitles" / f"{name}.srt").write_text("\n".join(srt), "utf-8")
    out = V / "exports" / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    return out, off


if __name__ == "__main__":
    o, total = assemble(sys.argv[1], sys.argv[2])
    print(o, total)
