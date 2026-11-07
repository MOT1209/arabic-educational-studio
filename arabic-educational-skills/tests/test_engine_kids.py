"""اختبارات طبقة الأطفال في المحرك: تطابق تقسيم الحروف مع بايثون، بقاء اتصال الحروف عند التلوين، وحدود السبورة."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
pw = pytest.importorskip("playwright.sync_api")

from studio.systems.arabic_language import letters as L  # noqa: E402
from studio.systems.arabic_language.bank import all_entries  # noqa: E402
from studio.systems.kids_learning.alphabet import build_letter_lesson  # noqa: E402
from studio.systems.kids_learning.converter import lesson_to_master_script  # noqa: E402
import render_scene as R  # noqa: E402


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    root = tmp_path_factory.mktemp("proj")
    (root / "assets" / "fonts").mkdir(parents=True)
    for f in (ROOT / "engine" / "fonts").glob("*.woff2"):
        shutil.copy2(f, root / "assets" / "fonts" / f.name)
    V = root / "video-01"
    V.mkdir()
    doc = lesson_to_master_script(build_letter_lesson("ا", target_seconds=300))
    (V / "master-script.json").write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
    return V, doc


@pytest.fixture(scope="module")
def page(project):
    V, doc = project
    html, _ = R.write_html(V, doc, "scene_07")
    with pw.sync_playwright() as p:
        br = R.launch(p)
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(html.as_uri())
        pg.evaluate("window.ready")
        pg.errors = errs
        yield pg
        br.close()


def test_cluster_count_matches_python(page):
    words = sorted({e["word"] for e in all_entries()})
    js = page.evaluate("ws => ws.map(w => clusterize(w).length)", words)
    py = [len([c for c in L.clusters(w) if c["kind"] == "letter"]) for w in words]
    bad = [(w, a, b) for w, a, b in zip(words, js, py) if a != b]
    assert not bad, bad[:5]


def test_joining_survives_colour_spans(page):
    """نرسم كل كلمة بنص واحد ثم مقسّمة إلى span لكل حرف (كما يفعل تظليل الحرف)؛ لا فرق بصري يُعتدّ به."""
    np = pytest.importorskip("numpy")
    from PIL import Image
    import io
    font = (ROOT / "engine/fonts/noto-sans-arabic-arabic-700-normal.woff2").as_uri()
    words = sorted({e["word"] for e in all_entries()})
    page.set_content(f"<style>@font-face{{font-family:AM;src:url('{font}');font-weight:700}}body{{margin:0;background:#fff}}"
                     "#a,#b{font:700 90px/2.2 AM;direction:rtl;color:#000;padding:10px 20px;width:760px;height:200px;overflow:visible}"
                     "</style><div id=a>x</div><div id=b>x</div>")
    assert page.evaluate("document.fonts.load('700 90px AM').then(r => r.length)") == 1, "font did not load: test would be vacuous"
    bad = []
    for w in words:
        page.evaluate("""w => { document.getElementById('a').textContent = w; const b = document.getElementById('b'); b.innerHTML = '';
            (w.match(/\\p{L}\\p{M}*|[^\\p{L}\\p{M}]+/gu) || []).forEach(p => { const s = document.createElement('span'); s.textContent = p; b.appendChild(s); }); }""", w)
        A = np.array(Image.open(io.BytesIO(page.locator("#a").screenshot())).convert("L"), dtype=int)
        B = np.array(Image.open(io.BytesIO(page.locator("#b").screenshot())).convert("L"), dtype=int)
        if (np.abs(A - B) > 96).sum() > 0.005 * max(1, (A < 128).sum()):
            bad.append(w)
    assert not bad, f"joining/shaping changed when split into spans: {bad[:5]}"


def test_no_js_errors_and_board_bounds(project, page):
    V, doc = project
    problems, errs = [], page.errors
    for sc in doc["scenes"]:
        html, _ = R.write_html(V, doc, sc["id"])
        page.goto(html.as_uri())
        page.evaluate("window.ready")
        for frac in (0.3, 0.6, 0.9):
            bad = page.evaluate(f"auditAt({sc['duration_seconds'] * frac})")
            if bad:
                problems.append((sc["id"], frac, bad[:1]))
    assert not errs, errs[:3]
    assert not problems, problems[:5]
