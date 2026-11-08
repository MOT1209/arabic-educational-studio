"""اختبارات 4.0: خطة الدرس العامة (أي مادة) ومحرك Remotion."""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.lesson_plan import plan as P  # noqa: E402
from studio.systems.kids_learning.alphabet import build_letter_lesson  # noqa: E402
from studio.systems.kids_learning.to_plan import lesson_to_plan  # noqa: E402

EX = ROOT / "examples" / "plans"
PLANS = sorted(EX.glob("*.plan.json"))


def _p(name):
    return P.load(EX / f"{name}.plan.json")


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.stem)
def test_examples_valid(path):
    E, _ = P.validate(P.load(path))
    assert not E, E


def test_examples_cover_different_subjects_ages_formats():
    plans = [P.load(p) for p in PLANS]
    assert len({p["subject"] for p in plans}) >= 3
    assert len({p["audience"]["age_band"] for p in plans}) >= 3
    assert {f for p in plans for f in p["formats"]} >= {"16:9", "9:16", "1:1"}
    assert len({p["style"]["theme"] for p in plans}) >= 3


@pytest.mark.parametrize("mutate,msg", [
    (lambda p: p["blocks"][0].update(type="banana"), "نوع غير معروف"),
    (lambda p: p["blocks"][1].update(id=p["blocks"][0]["id"]), "id مكرر"),
    (lambda p: p["blocks"][1].update(id="a__b"), "بلا '__'"),
    (lambda p: p["audience"].update(age_band="baby"), "age_band"),
    (lambda p: p["style"].update(theme="neon"), "style.theme"),
    (lambda p: p.update(formats=["4:3"]), "صيغة غير مدعومة"),
    (lambda p: p["blocks"][1].update(text="الْكِتَابُ ی"), "فارسية"),
    (lambda p: p["blocks"][1].update(text="كَتَبَُ"), "حركتان"),
])
def test_validator_rejects(mutate, msg):
    p = _p("inna")
    mutate(p)
    E, _ = P.validate(p)
    assert any(msg in e for e in E), E


def test_quiz_rules():
    p = _p("inna")
    q = next(b for b in p["blocks"] if b["type"] == "quiz")
    q["answer_index"] = 9
    assert any("answer_index" in e for e in P.validate(p)[0])
    q["answer_index"], q["options"] = 0, ["أ", "أ"]
    assert any("مكررة" in e for e in P.validate(p)[0])
    q["options"], q["listening"], q["question"] = ["بَ", "بِ"], True, "اسْمَعُوا: بَ"
    assert any("استماع" in e for e in P.validate(p)[0])


def test_highlight_must_match_exactly():
    p = _p("inna")
    ex = next(b for b in p["blocks"] if b["type"] == "example" and b.get("highlight"))
    ex["highlight"] = ["الطالب"]          # بلا تشكيل
    assert any("التلوين" in e for e in P.validate(p)[0])


def test_timeline_quiz_and_say_with_me_segments():
    p = _p("water-cycle")
    tl = P.timeline(p)
    q = next(b for b in tl["blocks"] if b["type"] == "quiz")
    kinds = [(s["kind"], s.get("label")) for s in q["segments"]]
    assert kinds == [("speech", None), ("pause", "think"), ("speech", "reveal")]
    s = next(b for b in tl["blocks"] if b["type"] == "say_with_me")
    assert [x["kind"] for x in s["segments"]] == ["speech", "speech", "pause"]
    assert tl["total_seconds"] == pytest.approx(sum(b["seconds"] for b in tl["blocks"]), abs=0.05)


def test_age_changes_pacing():
    a, b = _p("water-cycle"), _p("water-cycle")
    a["audience"]["age_band"], b["audience"]["age_band"] = "preschool", "adult"
    assert P.timeline(a)["total_seconds"] > P.timeline(b)["total_seconds"] * 1.4


def test_recorded_audio_extends_block(tmp_path):
    p = _p("inna")
    first = P.voice_lines(p)[0]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=200:duration=9",
                    str(tmp_path / f"{first['id']}.wav")], check=True)
    base = P.timeline(p)
    tl = P.timeline(p, tmp_path)
    assert tl["blocks"][0]["seconds"] > base["blocks"][0]["seconds"] + 4
    assert first["id"] not in tl["missing_audio"] and len(tl["missing_audio"]) == len(P.voice_lines(p)) - 1


def test_render_props_and_listening_caption_hidden():
    p = lesson_to_plan(build_letter_lesson("ب", profile="preschool"))
    for fmt, (w, h) in P.FORMATS.items():
        pr = P.render_props(p, fmt)
        assert pr["props_version"] == "1.0"
        assert (pr["width"], pr["height"]) == (w, h)
        assert pr["durationInFrames"] == pr["blocks"][-1]["from"] + pr["blocks"][-1]["frames"]
    pr = P.render_props(p, "9:16")
    lq = next(b for b in pr["blocks"] if b["type"] == "quiz" and b.get("listening"))
    ans = lq["options"][lq["answer_index"]]
    window = [c for c in pr["captions"] if lq["from"] <= c["from"] < lq["from"] + lq["frames"]]
    pre_reveal = [c for c in window if c["from"] < lq["from"] + next(s["from"] for s in lq["segments"] if s.get("label") == "reveal")]
    assert pre_reveal and all(ans not in c["text"] for c in pre_reveal)
    srt = P.srt(pr)
    assert srt.startswith("1\n00:00:")


def test_letter_lesson_to_plan_every_letter():
    from studio.systems.arabic_language import letters as L
    for letter in L.LETTER_ORDER:
        p = lesson_to_plan(build_letter_lesson(letter, profile="preschool"))
        E, _ = P.validate(p)
        assert not E, (letter, E)
        types = {b["type"] for b in p["blocks"]}
        assert {"letter", "word", "say_with_me", "quiz"} <= types


def test_glyph_data_has_all_letters_with_face():
    g = json.loads((ROOT / "remotion" / "src" / "data" / "glyphs.json").read_text("utf-8"))["glyphs"]
    assert set(g) == P.ARABIC_LETTERS
    for ch, v in g.items():
        x0, y0, x1, y1 = v["bounds"]
        assert x0 - 5 <= v["face"]["x"] <= x1 + 5 and y0 - 5 <= v["face"]["y"] <= y1 + 5, ch


def test_cli_validate_and_voice(tmp_path):
    r = subprocess.run([sys.executable, "-m", "studio", "plan", "validate", str(EX / "inna.plan.json")], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["ok"]
    bad = _p("inna")
    bad["blocks"][0]["type"] = "x"
    (tmp_path / "bad.json").write_text(json.dumps(bad, ensure_ascii=False), "utf-8")
    r = subprocess.run([sys.executable, "-m", "studio", "plan", "validate", str(tmp_path / "bad.json")], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 1
    r = subprocess.run([sys.executable, "-m", "studio", "plan", "voice", str(EX / "inna.plan.json"), "--out", str(tmp_path / "v")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
    assert "b07__answer" in (tmp_path / "v" / "voice-lines.md").read_text("utf-8")


needs_engine = pytest.mark.skipif(not (shutil.which("node") and (ROOT / "remotion" / "node_modules" / "remotion").exists()),
                                  reason="Remotion غير مثبت")


@pytest.mark.skipif(not shutil.which("node"), reason="node غير مثبت")
def test_render_refuses_props_without_version():
    """render.mjs لا يقبل props بلا props_version، ويرفض إصدارًا رئيسيًا غير مدعوم."""
    guard = json.dumps((ROOT / "remotion" / "props-version.mjs").as_uri())
    script = f"""
import {{propsVersionError}} from {guard};
const cases = [[{{}}, true], [{{props_version: '1.4'}}, false], [{{props_version: 1}}, false], [{{props_version: '2.0'}}, true]];
for (const [props, mustFail] of cases) {{
  const message = propsVersionError(props);
  if (Boolean(message) !== mustFail) {{
    console.error(JSON.stringify(props) + ' -> ' + message);
    process.exit(1);
  }}
}}
"""
    r = subprocess.run([shutil.which("node"), "--input-type=module", "-e", script],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout


@needs_engine
def test_stills_render_all_formats(tmp_path):
    from studio.lesson_plan import render as R
    p = _p("water-cycle")
    p["blocks"] = p["blocks"][:3]
    rep = R.render(p, tmp_path, formats=["16:9", "9:16", "1:1"], stills_only=True)
    from PIL import Image
    for o in rep["outputs"]:
        assert len(o["stills"]) == 3
        im = Image.open(o["stills"][1])
        assert im.size == P.FORMATS[o["format"]]
        assert len(set(im.convert("L").resize((64, 64)).tobytes())) > 20     # ليست صورة فارغة


@needs_engine
@pytest.mark.skipif(os.environ.get("AES_E2E") != "1", reason="تصيير فيديو كامل: AES_E2E=1")
def test_full_video_render(tmp_path):
    from studio.lesson_plan import render as R
    p = _p("inna")
    p["blocks"] = p["blocks"][:3]
    rep = R.render(p, tmp_path, formats=["9:16"])
    assert rep["outputs"][0]["technical_check"] == "passed", rep
