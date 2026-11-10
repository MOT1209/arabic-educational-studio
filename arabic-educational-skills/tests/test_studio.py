import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from studio.agents import subtitles
from studio.agents.interviewer import Interview, InterviewError
from studio.systems.arabic_language import letters as L
from studio.systems.arabic_language.orthography import split_sentence, validate_sentence
from studio.systems.arabic_language.review import ReviewLedger
from studio.systems.asset_manager.manager import AssetManager, AssetError
from studio.systems.kids_learning.alphabet import build_letter_lesson
from studio.systems.kids_learning.converter import lesson_to_master_script
from studio.systems.provider_manager.manager import ProviderManager, ProviderNotImplemented
from studio.systems.style_manager.manager import StyleManager, StyleError

ROOT = Path(__file__).resolve().parents[1]


# ---------- الإملاء ----------
def test_punctuation_inside_sentence_is_not_an_error():            # تراجع عن عطل اكتُشف في الاختبار الشامل
    for t in ["أُمّ: الْحَرْفُ فِي أَوَّلِ الْكَلِمَةِ.", "مَرْحَبًا يَا أَصْدِقَائِي!", "ا ≠ ى"]:
        assert not [i for i in validate_sentence(t)["issues"] if i["severity"] == "error" and i["code"] == "invalid_char"], t


def test_split_sentence_keeps_end_mark():
    assert split_sentence("هَذَا بَابٌ.") == (["هَذَا", "بَابٌ"], ".")


def test_persian_lookalikes_rejected():
    assert any(i["code"] for i in validate_sentence("كتابک")["issues"])


# ---------- دروس الحروف ----------
@pytest.mark.parametrize("letter", L.LETTERS)
def test_every_letter_lesson_builds_within_tolerance(letter):
    les = build_letter_lesson(letter, target_seconds=300)
    assert les["duration_report"]["within_tolerance"], (letter, les["duration_report"])
    assert not [w for w in les["warnings"] if w.get("severity") == "error"]
    doc = lesson_to_master_script(les)
    assert doc["scenes"] and all(d.get("id") for s in doc["scenes"] for d in s["dialogue"])


def test_lesson_requires_human_review_until_ledger_signs(tmp_path):
    les = build_letter_lesson("ب")
    assert les["review"]["needs_human_review"] and not les["review"]["all_approved"]
    led = ReviewLedger(tmp_path / "l.json")
    for it in les["review"]["needs_human_review"]:
        led.record(it["kind"], it["text"], "approved", "teacher")
    assert build_letter_lesson("ب", ledger=led)["review"]["all_approved"]


def test_alif_lesson_teaches_alif_maqsura_distinction():
    txt = json.dumps(build_letter_lesson("ا"), ensure_ascii=False)
    assert "ى" in txt


def test_invalid_letter_rejected():
    with pytest.raises(Exception):
        build_letter_lesson("x")


# ---------- المقابلة ----------
def _iv(tmp_path, **given):
    iv = Interview(tmp_path / "i.json", StyleManager(tmp_path / "s"))
    base = {"topic": "حرف الباء", "project_type": "kids_education", "letter": "ب", "duration": "300", "narration": "subtitles_only", "budget_usd": 0}
    base.update(given)
    while (q := iv.next_question()):
        iv.answer(q["id"], base[q["id"]]) if q["id"] in base else iv.accept_default(q["id"])
    return iv


def test_interview_one_question_at_a_time_and_confirm_gate(tmp_path):
    iv = _iv(tmp_path)
    with pytest.raises(InterviewError):
        iv.confirm("x")                      # لا اعتماد قبل عرض الملخص
    iv.summary()
    p = iv.confirm("hamad")
    assert p["approved"] and p["letter"] == "ب"


def test_interview_rejects_bad_letter_and_option(tmp_path):
    iv = Interview(tmp_path / "i.json", StyleManager(tmp_path / "s"))
    iv.answer("topic", "x")
    iv.answer("project_type", "kids_education")
    with pytest.raises(InterviewError):
        iv.answer("letter", "ء")
    with pytest.raises(InterviewError):
        iv.answer("narration", "telepathy")


def test_interview_answer_change_invalidates_summary(tmp_path):
    iv = _iv(tmp_path)
    iv.summary()
    iv.answer("duration", "120")
    with pytest.raises(InterviewError):
        iv.confirm("x")


# ---------- الأنماط ----------
def test_ten_styles_and_honest_render_support(tmp_path):
    m = StyleManager(tmp_path)
    a = m.all()
    assert len(a) >= 10 and a["classroom_2d_cartoon"]["render_support"] == "native"
    assert sum(s["render_support"] == "provider_required" for s in a.values()) >= 5


def test_style_crud_export_import_combine(tmp_path):
    m = StyleManager(tmp_path / "a")
    d = m.duplicate("classroom_2d_cartoon", "mine")
    assert d["id"] == "mine" and not d["builtin"]
    m.export("mine", tmp_path / "mine.json")
    m2 = StyleManager(tmp_path / "b")
    assert m2.import_file(tmp_path / "mine.json")["id"] == "mine"
    m.delete("mine")
    with pytest.raises(StyleError):
        m.delete("classroom_2d_cartoon")     # المدمج لا يُحذف
    h = m.combine("classroom_2d_cartoon", "kinetic_typography", "hyb", force=True)
    assert h["id"] == "hyb"


# ---------- المزوّدون ----------
def test_providers_never_pretend():
    pm = ProviderManager({"budget_usd": 0, "no_external_providers": True})
    assert all(p["status"] in ("implemented", "not_implemented") for p in pm.list())
    with pytest.raises(Exception):
        pm.require("speech")
    assert pm.health()["local_engine"]["ok"] in (True, False)


# ---------- الأصول ----------
def test_asset_versions_hash_and_tamper(tmp_path):
    f = tmp_path / "a.png"; f.write_bytes(b"one")
    am = AssetManager(tmp_path / "assets")
    am.register("bg1", "background", "خلفية", str(f), license="own")
    f.write_bytes(b"two"); am.add_version("bg1", str(f))
    assert len(am.get("bg1")["versions"]) == 2 and not am.verify()
    am.approve("bg1", "hamad")
    am.path_of("bg1", 1).write_bytes(b"tampered")
    assert am.verify()                        # يكشف العبث


# ---------- الترجمة ----------
def test_subtitles_no_orphans_and_srt_valid():
    doc = lesson_to_master_script(build_letter_lesson("ا", target_seconds=120))
    r = subtitles.build(doc, age="child")
    assert r["cues"] and r["srt"].startswith("1\n") and "-->" in r["srt"] and r["vtt"].startswith("WEBVTT")


# ---------- CLI ----------
def run(*a):
    return subprocess.run([sys.executable, "-m", "studio", *a], cwd=ROOT, capture_output=True, text=True)


def test_cli_lesson_and_new_status(tmp_path):
    r = run("lesson", "ت", "--out", str(tmp_path / "t"))
    assert r.returncode == 0 and (tmp_path / "t" / "master-script.json").exists()
    assert run("new", str(tmp_path / "pp"), "--name", "x").returncode == 0
    s = run("status", str(tmp_path / "pp"))
    assert s.returncode == 0 and json.loads(s.stdout)["approval_log_issues"] == []
    assert run("status", str(tmp_path / "missing")).returncode != 0


# ---------- شامل (بطيء: تصيير حقيقي ~8 د) ----------
@pytest.mark.skipif(not os.environ.get("AES_E2E"), reason="set AES_E2E=1 to run the full render (slow)")
def test_e2e_alif_video(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "e2e_alif.py"), str(tmp_path / "e2e")], capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]


# ---------- النموذج الصوتي المحلي (منفذ بلا نموذج) ----------
def _fake_tts(tmp_path, body):
    s = tmp_path / "fake_tts.py"
    s.write_text(body, "utf-8")
    return f"{sys.executable} {s} {{text_file}} {{out}}"


def test_local_tts_unconfigured_is_not_implemented(monkeypatch):
    monkeypatch.delenv("AES_LOCAL_TTS_CMD", raising=False)
    pm = ProviderManager()
    assert pm.get("local_tts")["status"] == "not_implemented"
    with pytest.raises(ProviderNotImplemented):
        pm.require("speech")


def test_local_tts_with_command_synthesizes(tmp_path):
    cmd = _fake_tts(tmp_path, "import sys\nopen(sys.argv[2],'wb').write(b'RIFF'+open(sys.argv[1],'rb').read())\n")
    pm = ProviderManager(tts_config={"cmd": cmd})
    assert pm.require("speech")["id"] == "local_tts"
    out = pm.synthesizer().synthesize("بَاب", tmp_path / "a" / "x.wav")
    assert Path(out).stat().st_size > 4


def test_local_tts_failures_are_reported(tmp_path):
    from studio.providers.local_tts import LocalTTSError
    pm = ProviderManager(tts_config={"cmd": _fake_tts(tmp_path, "import sys; sys.exit(3)\n")})
    with pytest.raises(LocalTTSError):
        pm.synthesizer().synthesize("x", tmp_path / "o.wav")
    pm = ProviderManager(tts_config={"cmd": _fake_tts(tmp_path, "pass\n")})          # ينجح ولا يكتب شيئاً
    with pytest.raises(LocalTTSError):
        pm.synthesizer().synthesize("x", tmp_path / "o2.wav")
    assert not ProviderManager(tts_config={"cmd": "no-such-binary-xyz {text_file} {out}"}).get("local_tts")["status"] == "implemented"


def test_style_interview_and_letter_song():
    from studio.agents import style_interview as SI
    from studio.systems.kids_song.letter_song import build_song_plan
    from studio.lesson_plan import plan as P
    assert SI.questions_for("ب")[0]["key"] == "style" and any(q["key"] == "audio" for q in SI.questions_for("ب"))
    assert not any(q["key"] == "audio" for q in SI.questions_for("الخبر"))
    r = SI.build_request("ب", {"style": "song", "audio": "both"})
    assert r["variants"] == ["with_rhythm", "vocals_only"] and r["generator"] == "kids_song.letter_song"
    import pytest
    with pytest.raises(ValueError):
        SI.build_request("الخبر", {"style": "song"})
    for l in "بتم":
        E, _ = P.validate(build_song_plan(l))
        assert not E, E
    bad = build_song_plan("ب"); bad["style"]["font"] = "comic"
    assert any("style.font" in e for e in P.validate(bad)[0])


def test_song_words_always_have_pictures():
    import json
    from pathlib import Path
    from studio.systems.kids_song.letter_song import build_song_plan
    M = json.loads((Path(__file__).resolve().parent.parent / "assets" / "emoji_map.json").read_text("utf-8"))
    for l in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي":
        for b in build_song_plan(l)["blocks"]:
            if b["type"] == "word":
                assert b["concept"] in M, (l, b["word"])


def test_voice_local_batch_with_fake_silma(tmp_path, monkeypatch):
    """يتحقق من التوصيل (قراءة الخطة ← أسطر ← دفعة ← ملفات) بوحدة silma_tts مزيّفة؛ لا يختبر جودة SILMA الحقيقية."""
    import json, sys, types, wave
    from studio.systems.kids_song.letter_song import build_song_plan
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))
    import voice_local
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps(build_song_plan("ب"), ensure_ascii=False), "utf-8")
    ref = tmp_path / "ref.wav"
    with wave.open(str(ref), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * 2400)
    (tmp_path / "voice.config.json").write_text(json.dumps({"ref_audio": str(ref), "ref_text": "x"}), "utf-8")
    calls = []
    class FakeTTS:
        def __init__(self, **k): pass
        def infer(self, ref_file, ref_text, gen_text, file_wave, **k):
            calls.append(gen_text)
            with wave.open(file_wave, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * 4800)
    api = types.ModuleType("silma_tts.api"); api.SilmaTTS = FakeTTS
    monkeypatch.setitem(sys.modules, "silma_tts", types.ModuleType("silma_tts"))
    monkeypatch.setitem(sys.modules, "silma_tts.api", api)
    monkeypatch.setattr("silma_tts_cmd.install_audio_io_patch", lambda: None, raising=False)
    assert voice_local.main([str(plan)]) == 0
    n = len(list((tmp_path / "audio").glob("*.wav")))
    assert n == len(calls) > 3
    calls.clear()
    assert voice_local.main([str(plan)]) == 0 and not calls      # الاستكمال: لا يعيد الموجود
