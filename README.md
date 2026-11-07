# استوديو قناتي — YouTube & TikTok

استوديو إنتاج فيديوهات تعليمية باللغة العربية (نحو، صرف، إملاء، بلاغة، ...).

## القنوات
- **YouTube**: https://www.youtube.com/@%D9%85%D8%AF%D8%B1%D8%B3%D8%AA%D9%8A-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9 (مدرستي العربية)
- **TikTok**: https://www.tiktok.com/@arbic.skool

## الهيكل
```
AI vedio/
├── arabic-educational-skills/   # Skill + references + scripts
├── youtube/
│   ├── long-form/               # فيديوهات 16:9 (3-12 min)
│   ├── shorts/                  # YouTube Shorts (9:16, ≤60s)
│   ├── metadata/                # بيانات النشر
│   └── thumbnails/              # صور مصغّرة (1280×720)
├── tiktok/
│   ├── shorts/                  # مقاطع تيك توك (9:16, ≤60s)
│   ├── metadata/                # بيانات النشر
│   └── covers/                  # صور الغلاف (1080×1920)
├── projects/                    # مجلد لكل فيديو (master-script + config)
├── assets/
│   ├── branding/                # شعار، intro، outro
│   └── characters/              # بطاقات الشخصيات
└── exports/                     # الملفات النهائية
```

## الـ Workflow (حسب arabic-educational-skills/SKILL.md)
1. **بوابة أ**: تحليل الدرس + اعتماد الفكرة
2. **بوابة ب**: كتابة master-script.json/md → validate_script.py
3. **بوابة ج**: إنتاج مشهد تجريبي → اعتماد
4. **الإنتاج**: أصول → تحريك → صوت → مونتاج → تصدير → check_output.py

## المتطلبات (Dependencies)
- Python 3.x
- ffmpeg + ffprobe (في PATH)
- jsonschema (اختياري: `pip install jsonschema`)

## السكربتات
| السكربت | الوظيفة |
|---|---|
| `validate_script.py` | تحقق من السكيما + دلالات + تشكيل + hash |
| `voice_pack.py` | بناء قائمة أسطر للتسجيل/التوليد |
| `mux_audio.py` | تركيب الصوت على الفيديو |
| `check_output.py` | فحص تقني للملف النهائي (ffprobe + SRT) |

## ملاحظات
- grammar-bank.md يحتاج مراجعة معلم قبل النشر
- النص العربي يُركَّب برمجياً (HTML/SVG) — لا يُعتمد على مولدات الصور
- كل مشهد يحتاج `id` و `hash` (يُحسب بـ `validate_script.py --update-hashes`)
PYEOF