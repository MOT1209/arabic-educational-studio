"""وكيل الترجمة المكتوبة: SRT/VTT من master-script (أو من أزمنة مُعاد قياسها). تقسيم الأسطر الطويلة، حدّ أدنى للمدة، وفحص سرعة القراءة."""
CPS_LIMIT = {"child": 9, "preteen": 12, "teen": 15, "adult": 17}
HARAKAT = set("ًٌٍَُِّْٰ")


def _t(sec, vtt=False):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{'.' if vtt else ','}{ms:03d}"


def _wrap(words, max_chars):
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def _chunks(text, max_chars, max_lines):
    """يقسّم النص إلى شرائح متوازنة (بلا كلمة يتيمة): أصغر عدد شرائح تتسع كل منها في max_lines سطر."""
    words = text.split()
    if not words:
        return [""]
    for n in range(1, len(words) + 1):
        groups, acc, tot = [], [], sum(len(w) + 1 for w in words)
        per = tot / n
        run = 0
        for w in words:
            acc.append(w); run += len(w) + 1
            if run >= per and len(groups) < n - 1:
                groups.append(acc); acc, run = [], 0
        if acc:
            groups.append(acc)
        wrapped = [_wrap(g, max_chars) for g in groups]
        if all(len(x) <= max_lines for x in wrapped):
            return ["\n".join(x) for x in wrapped]
    return [" ".join(words)]


def build(master, *, age="child", diacritized=True, max_chars=34, max_lines=2, min_duration=1.0):
    cues, issues, offset = [], [], 0.0
    cps_max = CPS_LIMIT[age]
    for sc in master["scenes"]:
        for d in sc.get("dialogue", []):
            text = d["text_diacritized"] if diacritized else d["text_plain"]
            if d.get("caption_text"):          # نص عرض بديل (مثلاً سؤال استماع لا يجوز أن يكشف إجابته)
                text = d["caption_text"]
            parts = _chunks(text, max_chars, max_lines)
            span = d["end"] - d["start"]
            weights = [max(1, len(p.replace("\n", " "))) for p in parts]
            t0 = offset + d["start"]
            for p, w in zip(parts, weights):
                dur = span * w / sum(weights)
                cues.append({"start": t0, "end": t0 + max(dur, min(min_duration, span)), "text": p, "line_id": d.get("id")})
                t0 += dur
        offset += sc["duration_seconds"]
    for i in range(len(cues) - 1):                        # لا تداخل بين الشرائح
        if cues[i]["end"] > cues[i + 1]["start"]:
            cues[i]["end"] = cues[i + 1]["start"]
    for i, c in enumerate(cues, 1):
        letters = sum(1 for ch in c["text"] if ch.isalpha() and ch not in HARAKAT)
        d = c["end"] - c["start"]
        if d <= 0:
            issues.append(f"cue {i}: non-positive duration")
        elif letters / d > cps_max:
            issues.append(f"cue {i}: reading speed {letters / d:.1f} chars/s > {cps_max} for {age}")
    srt = "\n".join(f"{i}\n{_t(c['start'])} --> {_t(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1))
    vtt = "WEBVTT\n\n" + "\n".join(f"{_t(c['start'], True)} --> {_t(c['end'], True)}\n{c['text']}\n" for c in cues)
    return {"srt": srt, "vtt": vtt, "cues": cues, "issues": issues}
