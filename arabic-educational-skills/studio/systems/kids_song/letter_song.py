"""قالب «أنا الحرف…» — أنشودة حرف قصيرة (30–45 ث) للأطفال، تُبنى من بنك الكلمات الموثَّق.
الكلمات الغنائية أصلية تُولَّد هنا (لا تُنسخ من أي أنشودة موجودة). تُخرج خطة lesson-plan v1 عادية
فيصيّرها محرك Remotion نفسه، مع وسم song يحدد نسختي الصوت: with_rhythm (إيقاع) و vocals_only (أصوات بلا آلات)."""
import json
from pathlib import Path
from ..arabic_language import bank
from ..kids_learning import alphabet

HARAKAT = [("َ", "فَتْحَة"), ("ُ", "ضَمَّة"), ("ِ", "كَسْرَة")]


def _letter_name(letter):
    try:
        return alphabet.build_letter_lesson(letter, "ar")["name"]
    except Exception:
        return letter


def build_song_plan(letter, *, n_words=3, formats=("9:16",), theme="classroom", font="playpen",
                    variants=("with_rhythm", "vocals_only"), tempo_bpm=96):
    emap = json.loads((Path(__file__).resolve().parents[3] / "assets" / "emoji_map.json").read_text("utf-8"))
    cands = [e for e in bank.words_for(letter, "initial") if e.get("illustrable")]
    # الكلمات التي لها صورة أولاً: لا يظهر في الفيديو مربع إنجليزي فارغ
    cands.sort(key=lambda e: e["concept_en"] not in emap)
    pic = [e for e in cands if e["concept_en"] in emap]
    words = (pic if len(pic) >= 2 else cands)[:n_words]   # عدد أقل بصور أفضل من كلمة بلا صورة
    if len(words) < 2:
        raise ValueError(f"كلمات الحرف {letter} في البنك قليلة للأنشودة (المتاح {len(words)}، المطلوب 2 على الأقل)")
    name = _letter_name(letter)
    syl = " ".join(letter + h for h, _ in HARAKAT)
    blocks, n = [], 0

    def nid():
        nonlocal n
        n += 1
        return f"b{n:02d}"

    blocks.append({"id": nid(), "type": "letter", "letter": letter, "name": name, "trace": False,
                   "narration": f"أَنَا حَرْفُ {name}!"})
    blocks.append({"id": nid(), "type": "say_with_me", "text": syl, "cue": "غَنُّوا مَعِي",
                   "narration": f"{syl.replace(' ', '، ')}."})
    for e in words:
        w = e["word"]
        blocks.append({"id": nid(), "type": "word", "word": w, "highlight_letters": [0], "concept": e["concept_en"],
                       "hold_seconds": 2.6, "narration": f"أَنَا {name} فِي {w}!"})
    blocks.append({"id": nid(), "type": "say_with_me", "text": syl, "cue": "مَعًا", "narration": f"{syl.replace(' ', '، ')}!"})
    q = words[0]
    blocks.append({"id": nid(), "type": "outro", "heading": "شُكْرًا لَكُمْ!",
                   "narration": f"مَنْ يَعْرِفُ كَلِمَةً أُخْرَى تَبْدَأُ بِحَرْفِ {name}؟ اكْتُبُوهَا فِي التَّعْلِيقَاتِ!"})
    return {
        "plan_version": "1.0", "slug": f"song-{letter}", "title": f"أَنَا حَرْفُ {name}",
        "subject": "arabic_letters", "audience": {"age_band": "preschool", "lang": "ar"},
        "formats": list(formats), "style": {"theme": theme, "font": font},
        "narrator": {"avatar": "letter_buddy", "avatar_letter": letter},
        "source": {"generator": "kids_song.letter_song", "review_pending": len(words)},
        "song": {"tempo_bpm": tempo_bpm, "variants": list(variants), "original_lyrics": True,
                 "note": "نسخة vocals_only بلا آلات موسيقية (يفضّلها كثير من الأسر)؛ with_rhythm بإيقاع خفيف"},
        "blocks": blocks,
    }
