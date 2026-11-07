"""اختبارات الإصدار 3.1: الشدة، ملف preschool، التمارين الأربعة، ملف المراجعة."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.systems.arabic_language import letters as L  # noqa: E402
from studio.systems.arabic_language.syllables import syllable_texts, syllabify  # noqa: E402
from studio.systems.kids_learning.alphabet import build_letter_lesson, QUIZ_KINDS, SIMILAR  # noqa: E402
from studio.systems.kids_learning.converter import lesson_to_master_script  # noqa: E402


@pytest.mark.parametrize("word,expected", [
    ("بَطَّة", ["بَطْ", "طَة"]),
    ("قُبَّعَة", ["قُبْ", "بَ", "عَة"]),
    ("سَبُّورَة", ["سَبْ", "بُو", "رَة"]),
    ("تُفَّاحَة", ["تُفْ", "فَا", "حَة"]),
    ("أُمّ", ["أُمّ"]),                       # شدة الوقف في الآخر تبقى
    ("مَدْرَسَة", ["مَدْ", "رَ", "سَة"]),
    ("بَقَرَة", ["بَ", "قَ", "رَة"]),
])
def test_shadda_syllables(word, expected):
    assert syllable_texts(word) == expected


def test_geminated_index_in_two_groups():
    assert syllabify("بَطَّة") == [[0, 1], [1, 2]]


def test_preschool_has_no_shadda_in_shown_words():
    for letter in L.LETTER_ORDER:
        les = build_letter_lesson(letter, profile="preschool")
        for u in les["units"]:
            d = u["display"]
            for key in ("word",):
                if d.get(key):
                    assert L.SHADDA not in d[key], (letter, u["id"], d[key])
            for s in d.get("syllables", []):
                assert L.SHADDA not in s, (letter, s)


def test_preschool_duration_all_letters_2_to_3_minutes():
    for letter in L.LETTER_ORDER:
        rep = build_letter_lesson(letter, profile="preschool")["duration_report"]
        assert rep["within_tolerance"], (letter, rep)
        assert 120 <= rep["total_seconds"] <= 200, (letter, rep)


def test_preschool_call_and_response_and_fixed_pause():
    les = build_letter_lesson("ب", profile="preschool")
    words = [u for u in les["units"] if u["type"] == "word"]
    assert words and all("قُولُوا مَعِي" in u["text"] for u in words)
    assert all(2.5 <= u["pause_seconds"] <= 4.0 for u in words)


def test_four_quiz_kinds_every_letter():
    for letter in L.LETTER_ORDER:
        for profile in ("preschool", "standard"):
            q = build_letter_lesson(letter, profile=profile)["quiz"]
            assert [x["kind"] for x in q] == list(QUIZ_KINDS), (letter, profile, q)
            for x in q:
                assert x["answer"] in x["options"], x
                assert len(x["options"]) == 3


def test_quiz_answer_position_varies_across_letters():
    idx = set()
    for letter in L.LETTER_ORDER:
        for x in build_letter_lesson(letter, profile="preschool")["quiz"]:
            if x["kind"] in ("which_starts_with", "sound_choice", "find_letter"):
                idx.add(x["options"].index(x["answer"]))
    assert idx == {0, 1, 2}


def test_similar_letters_are_valid_and_distinct():
    for letter, sims in SIMILAR.items():
        assert letter in L.LETTERS
        assert letter not in sims
        assert all(c in L.LETTERS for c in sims), (letter, sims)


def test_converter_renders_new_quiz_kinds():
    doc = lesson_to_master_script(build_letter_lesson("ب", profile="preschool"))
    quizzes = [v for sc in doc["scenes"] for v in sc["visuals"] if v["type"] == "quiz"]
    assert len(quizzes) == 4
    assert {q["layout"] for q in quizzes} == {"rows", "row"}
    cues = [v for sc in doc["scenes"] for v in sc["visuals"] if v["type"] == "cue"]
    assert cues


def test_master_script_passes_validator(tmp_path):
    doc = lesson_to_master_script(build_letter_lesson("ب", profile="preschool"))
    p = tmp_path / "master-script.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_script.py"), str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def _cli(*a):
    return subprocess.run([sys.executable, "-m", "studio", *a], cwd=ROOT, capture_output=True, text=True)


@pytest.mark.parametrize("ext", ["xlsx", "csv"])
def test_review_sheet_roundtrip(tmp_path, ext):
    if ext == "xlsx":
        pytest.importorskip("openpyxl")
    sheet = tmp_path / f"review.{ext}"
    r = _cli("review", "export", "--out", str(sheet))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["rows"] > 250
    if ext == "csv":
        rows = list(csv.reader(sheet.open(encoding="utf-8-sig")))
        rows[1][9], rows[2][9], rows[2][10] = "موافق", "تعديل", "أَرْنَبٌ"
        with sheet.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(rows)
        first, second = rows[1][2], rows[2][2]
    else:
        from openpyxl import load_workbook
        wb = load_workbook(sheet)
        ws = wb.worksheets[0]
        ws["J2"], ws["J3"], ws["K3"] = "موافق", "تعديل", "أَرْنَبٌ"
        first, second = ws["C2"].value, ws["C3"].value
        wb.save(sheet)
    ledger = tmp_path / "review.json"
    assert _cli("review", "import", str(sheet), "--ledger", str(ledger), "--reviewer", "").returncode != 0
    r = _cli("review", "import", str(sheet), "--ledger", str(ledger), "--reviewer", "حمد")
    assert r.returncode == 0, r.stderr
    rec = json.loads(r.stdout)["recorded"]
    assert rec == {"approved": 1, "rejected": 0, "needs_change": 1}
    st = json.loads(_cli("review", "status", "--ledger", str(ledger), "--kind", "word", "--text", first).stdout)
    assert st["status"] == "approved"
    # المطلوب تعديله لا يُستعمل في الدرس
    from studio.systems.arabic_language.review import ReviewLedger
    les = build_letter_lesson("ا", profile="standard", ledger=ReviewLedger(ledger))
    used = [e["word"] for pos in ("initial", "medial", "final") for e in les["examples"][pos]]
    assert second not in used


def test_lessons_match_learning_lesson_schema():
    from studio.core.schema import validate
    schema = json.loads((ROOT / "schemas" / "learning-lesson.schema.json").read_text("utf-8"))
    for letter in ("ا", "ب", "ه", "ي"):
        for profile in ("preschool", "standard"):
            validate(build_letter_lesson(letter, profile=profile), schema)
