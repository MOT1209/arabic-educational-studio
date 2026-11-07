"""يُولّد ملف SRT من master-script.json.
الاستخدام: python gen_srt.py <مجلد المشروع> [<اسم الملف>]"""
import json, sys
from pathlib import Path

def srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python gen_srt.py <مجلد المشروع> [<اسم الملف>]")
        return 2
    proj = Path(sys.argv[1]).resolve()
    out_name = sys.argv[2] if len(sys.argv) > 2 else "lesson.srt"
    script_path = proj / "master-script.json"
    if not script_path.exists():
        print(f"خطأ: master-script.json غير موجود في {proj}")
        return 1
    doc = json.loads(script_path.read_text(encoding="utf-8"))

    out_dir = proj / "subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name

    cues = []
    off = 0.0
    for sc in doc.get("scenes", []):
        for d in sc.get("dialogue", []):
            start = off + d.get("start", 0)
            end = off + d.get("end", 0)
            text = d.get("text_diacritized", d.get("text_plain", ""))
            if text.strip():
                cues.append((start, end, text))
        off += sc.get("duration_seconds", 0)

    with open(out_path, "w", encoding="utf-8") as f:
        for i, (s, e, t) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n\n")
    print(f"تم: {len(cues)} مقطع -> {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
PYEOF