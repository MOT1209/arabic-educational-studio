"""ملف مراجعة سهل لبنك الكلمات وجمل الدروس: تصدير إلى Excel (أو CSV) يملؤه المراجع، ثم استيراد قراراته
إلى ReviewLedger. القرار يُكتب بالعربية (موافق / مرفوض / تعديل) أو بالإنجليزية (approved / rejected / needs_change).

لا يجعل الاستيراد أي مثال «معتمداً» إلا إذا كتب المراجع قراراً في الصف؛ الصفوف الفارغة تُتجاهل.
"""
import csv
import unicodedata
from pathlib import Path

from . import letters as L
from .bank import BANK
from .review import ReviewLedger
from .syllables import has_shadda, syllable_texts

HEADERS = ["الحرف", "النوع", "النص", "الموضع", "المعنى (EN)", "التقطيع", "فيه شدة", "في درس الحرف",
           "الحالة الحالية", "القرار", "التصحيح المقترح", "ملاحظة"]
KEYS = ["letter", "kind", "text", "position", "meaning_en", "syllables", "shadda", "in_lesson",
        "current", "decision", "correction", "note"]
POS_AR = {"initial": "أول", "medial": "وسط", "final": "آخر", "": ""}
KIND_AR = {"word": "كلمة", "sentence": "جملة"}
STATUS_AR = {"approved": "موافق", "rejected": "مرفوض", "needs_change": "تعديل", "unreviewed": "لم يُراجَع"}
DECISION_MAP = {"موافق": "approved", "مرفوض": "rejected", "تعديل": "needs_change",
                "approved": "approved", "rejected": "rejected", "needs_change": "needs_change"}
CHOICES_AR = ("موافق", "مرفوض", "تعديل")


def _nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


def collect_rows(ledger=None, profile="preschool", letters=None):
    """صفوف المراجعة: كل كلمات البنك، وجملة درس كل حرف كما يولّدها الملف التعريفي المختار."""
    from ..kids_learning.alphabet import build_letter_lesson   # تجنّب الاستيراد الدائري
    rows = []
    for letter in letters or L.LETTER_ORDER:
        lesson = build_letter_lesson(letter, profile=profile, ledger=ledger)
        used = {_nfc(e["word"]) for pos in ("initial", "medial", "final") for e in lesson["examples"].get(pos, [])}
        for pos in ("initial", "medial", "final"):
            for e in BANK.get(letter, {}).get(pos, []):
                w = e["word"]
                st = ledger.status("word", w) if ledger else "unreviewed"
                rows.append({"letter": letter, "kind": "word", "text": w, "position": pos, "meaning_en": e["concept_en"],
                             "syllables": " | ".join(syllable_texts(w)), "shadda": "نعم" if has_shadda(w) else "",
                             "in_lesson": "نعم" if _nfc(w) in used else "", "current": st,
                             "decision": "", "correction": "", "note": ""})
        if lesson.get("sentence"):
            s = lesson["sentence"]["text"]
            st = ledger.status("sentence", s) if ledger else "unreviewed"
            rows.append({"letter": letter, "kind": "sentence", "text": s, "position": "",
                         "meaning_en": lesson["sentence"].get("translation_en", ""), "syllables": "",
                         "shadda": "نعم" if has_shadda(s) else "", "in_lesson": "نعم", "current": st,
                         "decision": "", "correction": "", "note": ""})
    return rows


def _display(r):
    return [r["letter"], KIND_AR[r["kind"]], r["text"], POS_AR[r["position"]], r["meaning_en"], r["syllables"],
            r["shadda"], r["in_lesson"], STATUS_AR.get(r["current"], r["current"]), r["decision"], r["correction"], r["note"]]


def export_sheet(path, ledger=None, profile="preschool", letters=None):
    """يكتب ملف المراجعة. ‎.xlsx (اتجاه من اليمين، قائمة منسدلة للقرار) إن توفّرت openpyxl، وإلا ‎.csv."""
    rows = collect_rows(ledger, profile, letters)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".xlsx":
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.worksheet.datavalidation import DataValidation
        except ImportError:
            path = path.with_suffix(".csv")
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "مراجعة"
            ws.sheet_view.rightToLeft = True
            ws.append(HEADERS)
            for r in rows:
                ws.append(_display(r))
            head = PatternFill("solid", fgColor="1F6FEB")
            todo = PatternFill("solid", fgColor="FFF4CC")
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = head
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            widths = [7, 8, 34, 8, 18, 22, 8, 10, 12, 11, 26, 30]
            for i, w in enumerate(widths):
                ws.column_dimensions[chr(65 + i)].width = w
            dv = DataValidation(type="list", formula1='"' + ",".join(CHOICES_AR) + '"', allow_blank=True,
                                showErrorMessage=True, errorTitle="قرار غير صالح", error="اختر: موافق أو مرفوض أو تعديل")
            ws.add_data_validation(dv)
            last = ws.max_row
            dv.add(f"J2:J{last}")
            for row in range(2, last + 1):
                ws[f"J{row}"].fill = todo
                ws[f"C{row}"].font = Font(size=16)
            ws.freeze_panes = "D2"
            ws.auto_filter.ref = f"A1:L{last}"
            help_ws = wb.create_sheet("طريقة المراجعة")
            help_ws.sheet_view.rightToLeft = True
            for line in ("1) اقرأ الكلمة بتشكيلها وتأكد من المعنى والنطق ومناسبتها لطفل 4–6 سنوات.",
                         "2) تحقق من عمود «التقطيع» (المقاطع كما تُعرض في الفيديو).",
                         "3) اختر القرار من القائمة: موافق / مرفوض / تعديل.",
                         "4) في حالة «تعديل» اكتب الصواب في «التصحيح المقترح». الكلمة لن تُستعمل حتى تُصحَّح في البنك.",
                         "5) الصفوف المميزة بـ«في درس الحرف = نعم» تظهر فعلاً في الدرس الحالي: ابدأ بها.",
                         "6) احفظ الملف ثم: python -m studio review import <الملف> --ledger review.json --reviewer \"اسمك\""):
                help_ws.append([line])
            help_ws.column_dimensions["A"].width = 110
            wb.save(path)
            return {"path": str(path), "rows": len(rows), "format": "xlsx"}
    with open(path, "w", encoding="utf-8-sig", newline="") as f:      # BOM كي يفتحه Excel بالعربية صحيحاً
        w = csv.writer(f)
        w.writerow(HEADERS)
        for r in rows:
            w.writerow(_display(r))
    return {"path": str(path), "rows": len(rows), "format": "csv"}


def _read_rows(path):
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = [str(h or "").strip() for h in next(it)]
        for vals in it:
            yield dict(zip(header, ["" if v is None else str(v) for v in vals]))
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            yield from csv.DictReader(f)


def import_sheet(path, ledger_path, reviewer):
    """يسجّل في السجل كل صف كُتب فيه قرار. يعيد ملخصاً بالأعداد والصفوف غير المفهومة."""
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer name is required (--reviewer)")
    led = ReviewLedger(ledger_path)
    kind_from_ar = {v: k for k, v in KIND_AR.items()}
    counts = {"approved": 0, "rejected": 0, "needs_change": 0}
    skipped, bad = 0, []
    for i, row in enumerate(_read_rows(path), start=2):
        dec = _nfc(row.get("القرار", ""))
        if not dec:
            skipped += 1
            continue
        verdict = DECISION_MAP.get(dec) or DECISION_MAP.get(dec.lower())
        kind = kind_from_ar.get(_nfc(row.get("النوع", "")))
        text = _nfc(row.get("النص", ""))
        if not verdict or not kind or not text:
            bad.append({"row": i, "decision": dec, "text": text})
            continue
        note = " · ".join(x for x in (_nfc(row.get("التصحيح المقترح", "")) and f"تصحيح: {_nfc(row.get('التصحيح المقترح', ''))}",
                                      _nfc(row.get("ملاحظة", ""))) if x)
        led.record(kind, text, verdict, reviewer, note)
        counts[verdict] += 1
    return {"recorded": counts, "skipped_empty": skipped, "unrecognized": bad, "ledger": str(ledger_path)}
