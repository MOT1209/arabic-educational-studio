#!/usr/bin/env python3
"""يبني حزمة التسجيل لكل سطر حوار: معرّف ثابت + النص المشكول + المدة المتاحة + بصمة النص.
python voice_pack.py <مجلد الفيديو> [<مجلد الخرج>]  → voice/voice-pack.csv و voice/voice-pack.txt
البصمة تسمح لـ mux_audio.py بكشف أي سطر تغيّر نصه بعد تسجيله."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aes_common import line_id, text_sha  # noqa: E402


def build_rows(doc):
    names = {c["id"]: c["name"] for c in doc["characters"]}
    rows, off = [], 0
    for sc in doc["scenes"]:
        for i, d in enumerate(sc.get("dialogue", []), 1):
            text = d.get("tts_text") or d["text_diacritized"]
            rows.append({"id": line_id(sc, i, d), "speaker": names.get(d["character"], d["character"]),
                         "emotion": d.get("emotion", ""), "text": text, "slot_seconds": round(d["end"] - d["start"], 2),
                         "start_in_video": round(off + d["start"], 2), "text_sha": text_sha(text)})
        off += sc["duration_seconds"]
    return rows


def main():
    V = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else V / "voice"
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads((V / "master-script.json").read_text("utf-8"))
    rows = build_rows(doc)
    if not rows:
        sys.exit("لا أسطر حوار في السيناريو")
    if any("id" not in d for sc in doc["scenes"] for d in sc.get("dialogue", [])):
        print("تنبيه: بعض الأسطر بلا id ثابت؛ شغّل validate_script.py --update-hashes قبل التسجيل كي لا تتغير الأسماء عند الإدراج")
    with open(out / "voice-pack.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(out / "voice-pack.txt", "w", encoding="utf-8") as f:
        f.write("سجّل كل سطر في ملف باسم معرّفه (wav أو mp3 أو m4a). المدة المتاحة بين قوسين؛ "
                "إن تجاوزتها فلا بأس، شغّل retime_from_audio.py بعد التسجيل.\n\n")
        for r in rows:
            f.write(f"{r['id']}  [{r['slot_seconds']} ث]  {r['speaker']}" + (f" ({r['emotion']})" if r["emotion"] else "")
                    + f"\n{r['text']}\n\n")
    print(len(rows), "سطراً ->", out)


if __name__ == "__main__":
    main()
