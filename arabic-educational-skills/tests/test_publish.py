import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publish_youtube as P  # noqa: E402


def test_fmt_ts():
    assert P.fmt_ts(0) == "0:00" and P.fmt_ts(65) == "1:05" and P.fmt_ts(3725) == "1:02:05"


def test_shift_srt_moves_every_cue():
    src = "1\n00:00:01,000 --> 00:00:02,500\nأ\n\n2\n00:01:00,000 --> 00:01:01,000\nب\n"
    txt, n = P.shift_srt(src, 3.0)
    assert n == 2 and "00:00:04,000 --> 00:00:05,500" in txt and "00:01:03,000 --> 00:01:04,000" in txt


def test_chapter_rules():
    ok = {"title": "t", "chapters": [{"t": 0, "title": "a"}, {"t": 20, "title": "b"}, {"t": 40, "title": "c"}]}
    assert P.validate_meta(ok, 100, 0)[0] == []
    assert P.validate_meta({**ok, "chapters": [{"t": 5, "title": "a"}, {"t": 20, "title": "b"}, {"t": 40, "title": "c"}]}, 100, 0)[0]   # لا يبدأ بـ0:00
    assert P.validate_meta({**ok, "chapters": [{"t": 5, "title": "a"}, {"t": 20, "title": "b"}, {"t": 40, "title": "c"}]}, 100, 3)[0] == []  # المقدمة تملأ 0:00
    assert P.validate_meta({**ok, "chapters": [{"t": 0, "title": "a"}, {"t": 5, "title": "b"}, {"t": 40, "title": "c"}]}, 100, 0)[0]       # < 10ث
    assert P.validate_meta({**ok, "chapters": [{"t": 0, "title": "a"}, {"t": 20, "title": "b"}, {"t": 140, "title": "c"}]}, 100, 0)[0]     # بعد النهاية
    assert P.validate_meta({"title": ""}, 10, 0)[0] and P.validate_meta({"title": "x" * 101}, 10, 0)[0]


def test_shorts_limits():
    e, w = P.validate_meta({"title": "t", "shorts": [{"name": "a", "start": 0, "end": 90}]}, 100, 0)
    assert not e and w
    assert P.validate_meta({"title": "t", "shorts": [{"name": "a", "start": 0, "end": 200}]}, 100, 0)[0]


@pytest.mark.skipif(subprocess.call(["which", "ffmpeg"], stdout=subprocess.DEVNULL) != 0, reason="no ffmpeg")
def test_end_to_end_loudness_and_offsets(tmp_path):
    def ff(*a):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)
    ff("-f", "lavfi", "-i", "testsrc=size=640x360:rate=30", "-f", "lavfi", "-i", "sine=f=300", "-af", "volume=-30dB", "-t", "30", "-c:v", "libx264", "-preset", "ultrafast", str(tmp_path / "m.mp4"))
    ff("-f", "lavfi", "-i", "color=c=blue:size=640x360:rate=30", "-t", "2", "-c:v", "libx264", "-preset", "ultrafast", str(tmp_path / "i.mp4"))   # بلا صوت
    (tmp_path / "s.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nس\n", "utf-8")
    (tmp_path / "p.json").write_text(json.dumps({"title": "ت", "intro": "i.mp4", "chapters": [{"t": 0, "title": "أ"}, {"t": 12, "title": "ب"}, {"t": 24, "title": "ج"}],
                                                  "shorts": [{"name": "k", "start": 1, "end": 6}]}), "utf-8")
    assert P.main([str(tmp_path / "m.mp4"), str(tmp_path / "p.json"), "--out", str(tmp_path / "o"), "--srt", str(tmp_path / "s.srt")]) == 0
    out = tmp_path / "o"
    li, _ = P.measure_output(out / "youtube.mp4")
    assert abs(li + 14) < 1.0
    assert abs(P.probe(out / "youtube.mp4")["duration"] - 32) < 0.5
    assert "00:00:03,000" in (out / "subtitles.srt").read_text("utf-8")
    d = (out / "description.txt").read_text("utf-8")
    assert "0:00 المقدمة" in d and "0:02 أ" in d
    i = P.probe(out / "shorts" / "k.mp4")
    assert (i["width"], i["height"]) == (1080, 1920)
