# استوديو قناتي — YouTube & TikTok

استوديو إنتاج فيديوهات تعليمية باللغة العربية (نحو، صرف، إملاء، بلاغة، ...) — من تطوير agenteer.

## القنوات

- **YouTube**: [`@مدرب_العربية`](https://www.youtube.com/@%D9%85%D8%AF%D8%B1%D8%B3%D8%AA%D9%8A-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9)  (مدرستي العربية)
- **TikTok**: [`@arbic.skool`](https://www.tiktok.com/@arbic.skool)

## الهيكل

```text
arabic-educational-studio/
├── arabic-educational-skills/     # الحزمة الأساسية
│   ├── SKILL.md                   # دستور العمل: البوابات ومسار الإنتاج
│   ├── engine/                    # محرك التصيير: قالب HTML، خطوط، build/assemble
│   ├── scripts/                   # التحقق، الصوت، الـ mux، فحص المخرجات
│   ├── studio/                    # Studio 3.0 CLI (python -m studio)
│   ├── references/                # السكيما، بنك النحو، ملفات الجمهور والمنصات
│   ├── schemas/  tests/  remotion/  docs/  examples/
├── youtube/
│   ├── long-form/                 # فيديوهات 16:9 (3-12 دقيقة)
│   ├── shorts/                    # YouTube Shorts (9:16، ≤60ث)
│   ├── metadata/                  # بيانات النشر (SEO، وسوم، وصف)
│   └── thumbnails/                # صور مصغّرة (1280×720)
├── tiktok/
│   ├── shorts/                    # مقاطع تيك توك (9:16، ≤60ث)
│   ├── metadata/                  # بيانات النشر
│   └── covers/                    # صور الغلاف (1080×1920)
├── projects/                      # مشروع لكل فيديو (master-script + video-brief)
├── assets/
│   ├── branding/                  # شعار، intro، outro
│   └── characters/                # بطاقات الشخصيات
├── tools/                         # 3 أدوات مضافة (انظر أدوات المشروع)
├── .github/workflows/ci.yml       # CI لكل مشروع
└── projects/<video>/exports/      # مخرجات التصيير — داخل كل مشروع، تُولَّد تلقائياً ومتجاهَلة في git
```

> لا يوجد `package.json` في الجذر: كل مشروع له اعتمادياته وأمر `npm` الخاص به. تشغيل `npm` من الجذر خطأ.

## سير العمل (حسب `arabic-educational-skills/SKILL.md`)

1. **بوابة أ**: تحليل الدرس + اعتماد الفكرة
2. **بوابة ب**: كتابة `master-script.json/md` → `validate_script.py`
3. **بوابة ج**: إنتاج مشهد تجريبي → اعتماد
4. **الإنتاج**: أصول → تحريك → صوت → مونتاج → تصدير → `check_output.py`

## المتطلبات

| المتطلب | الإصدار | لِمن |
|---|---|---|
| Python | ≥ 3.9 (CI: 3.12) | سكربتات الحزمة و`studio` |
| ffmpeg + ffprobe | في `PATH` | التصيير، الـ mux، فحص المخرجات |
| Node.js | ≥ 18.17 | `youtube-automation-agent` ومحرك Remotion |

## التثبيت

### 1) استنساخ المستودع

```bash
git clone https://github.com/MOT1209/arabic-educational-studio.git
cd arabic-educational-studio
```

### 2) ffmpeg

```bash
# Ubuntu / Debian
sudo apt install ffmpeg
```

```powershell
# Windows
winget install Gyan.FFmpeg
```

### 3) اعتماديات Python

```bash
python -m pip install pytest jsonschema pyyaml pillow numpy
```

`jsonschema` اختياري: عند غيابه يستخدم `validate_script.py` المدقق المدمج في `studio/core/schema.py`.

### 4) محرك التصيير (Remotion)

```bash
cd arabic-educational-skills/remotion
npm ci
npx remotion browser ensure
```

### 5) وكيل أتمتة YouTube

```bash
cd tools/youtube-automation-agent
npm ci
npx playwright install chromium    # على Linux أضف --with-deps
cp .env.example .env               # Windows/cmd: copy .env.example .env
```

املأ مفتاح مزوّد واحد على الأقل في `.env`، ثم:

```bash
npm run walkthrough    # إعداد تفاعلي: يشرح الخيارات ويختبر المفاتيح ويربط القناة
npm start              # http://localhost:3456
```

`npm run setup` بديل أقصر، و`npm run walkthrough` يشرح كل خيار.

## التحقق من البيئة

```bash
python arabic-educational-skills/scripts/doctor.py
```

يطبع ما هو متاح وما هو ناقص مع أمر التثبيت، ويخرج بالرمز 1 إن كان شيء ناقصاً. لا يثبّت شيئاً بنفسه.

## السكربتات

تُشغَّل من داخل `arabic-educational-skills/`:

| السكربت | الوظيفة |
|---|---|
| `scripts/validate_script.py` | تحقق من السكيما + دلالات + تشكيل + hash. الخيارات: `--update-hashes`، `--no-engine` |
| `scripts/doctor.py` | فحص البيئة قبل الإنتاج |
| `scripts/auto_tashkeel.py` | اقتراح تشكيل للنص |
| `scripts/validate_brief.py` | تحقق من `video-brief.json` قبل كتابة السيناريو |
| `scripts/voice_pack.py` | بناء قائمة أسطر للتسجيل/التوليد |
| `scripts/mux_audio.py` | تركيب الصوت على الفيديو |
| `scripts/gen_srt.py` | توليد ملف الترجمة SRT |
| `scripts/retime_from_audio.py` | إعادة توقيت الأسطر من مدة الصوت الحقيقية |
| `scripts/check_output.py` | فحص تقني للملف النهائي (ffprobe + SRT) |
| `scripts/aes_common.py` | مكتبة مشتركة (لا تُشغَّل مباشرة) |

`validate_script.py` و`check_output.py` و`mux_audio.py` و`retime_from_audio.py` و`auto_tashkeel.py` تقبل `--help`. أما `validate_brief.py` و`voice_pack.py` و`gen_srt.py` فتأخذ مساراً موضعياً بلا خيارات:

```bash
python scripts/validate_brief.py projects/<اسم-المشروع>/video-brief.json
python scripts/voice_pack.py projects/<اسم-المشروع>
python scripts/gen_srt.py projects/<اسم-المشروع>
```

ولخط الإنتاج الكامل:

```bash
python -m studio --help
```

يوفّر `new, status, step, submit, approve, reject, modify, regenerate, rewind, compare, resume, verify, interview, styles, providers, lesson, plan, review, assets, subtitles`.

## متغيرات البيئة

المصدر الوحيد للحقيقة هو `tools/youtube-automation-agent/.env.example` — كل متغير مشروح هناك مع قيمه الافتراضية. الأساسي منها:

| المتغير | الغرض |
|---|---|
| `OPENAI_API_KEY` أو `GEMINI_API_KEY` أو `OPENROUTER_API_KEY` … | مزوّد نص واحد على الأقل (التفاصيل في `docs/providers.md`) |
| `ELEVENLABS_API_KEY` | تعليق صوتي بجودة أعلى (اختياري؛ البديل OpenAI/Gemini) |
| `API_KEY` | عند ضبطه تصبح مسارات الـ API المعدِّلة تطلب ترويسة `x-api-key` |
| `HOST` / `PORT` | الاستماع افتراضياً على `127.0.0.1:3456`؛ `HOST=0.0.0.0` يكشف الداشبورد للشبكة، فاضبط `API_KEY` معه |
| `CHANNEL_NAME` / `DEFAULT_AUTHOR` / `TARGET_AUDIENCE` | هوية القناة المستخدمة في التوليد |
| `DEFAULT_PRIVACY_STATUS` | خصوصية الرفع، الافتراضي `private` |
| `FFMPEG_PATH` / `FFPROBE_PATH` | تجاوز مسار ffmpeg (الترتيب: `FFMPEG_PATH` ← `ffmpeg-static` ← `PATH`) |
| `YOUTUBE_REDIRECT_URI` | تجاوز loopback لـ OAuth (يتطلب بيانات Desktop app) |

`.env` و`config/credentials.json` متجاهَلان في git، ولا تُرفع أي مفاتيح.

## الاختبارات

```bash
cd arabic-educational-skills
python -m pytest tests -q
```

```bash
cd tools/youtube-automation-agent
npm run lint
npm test
```

## أدوات المشروع (Tools)

انظر `tools/README.md` — 3 مستودعات مضافة:

| المستودع | الوصف |
|---|---|
| `tools/elephant-goldfish-model/` (EGM) | إضافة (plugin) لـ Claude Code/Codex/Gemini لتصميم ومراجعة البرمجيات |
| `tools/youtube-agent-skill/` | 11 مهارة Claude لإدارة قناة YouTube (scripts, hooks, packaging, retention, shorts, viral, seo, chapters, audit) |
| `tools/youtube-automation-agent/` | وكيل أتمتة YouTube — self-hosted، من البحث إلى النشر بعد الموافقة |

## التشغيل الآلي (CI)

`.github/workflows/ci.yml` يبني كل مشروع في مهمة مستقلة على Ubuntu: `arabic-educational-skills` (pytest + Remotion)، `youtube-automation-agent` (`npm ci` + lint + test)، `youtube-agent-skill` (تحقق نحوي)، `elephant-goldfish-model` (pytest)، `elephant-goldfish-site` (Astro). ومهمة `CI` أخيرة تفشل إن لم تنجح كل المهام. تقارير المراجعة في `PHASE1_AUDIT.md` و`PHASE2_SECURITY_AUDIT.md`.

## ملاحظات

- `grammar-bank.md` يحتاج مراجعة معلم قبل النشر
- النص العربي يُركَّم برمجياً (HTML/SVG) — لا يُعتمد على مولدات الصور
- كل مشهد يحتاج `id` و `hash` (يُحسب بـ `validate_script.py --update-hashes`)
- `.gitignore` يغطي `node_modules/`، `.env`، `config/credentials.json`، `data/`، `uploads/`، `exports/`، وملفات الوسائط
- مجلدا `TIK TOK/` و`YOU TUBE/` بقايا قديمة خارج خط الإنتاج الحالي

## ملاحظة حول الترجمة

هذا القارئ أساسي باللغة العربية. ملفات الترجمة الأخرى متوفرة:
- `README.en.md` — الإنجليزية
- `README.de.md` — الألمانية

## الترخيص

MIT License — انظر LICENSE للمزيد من التفاصيل.

## الامتنان

شكر خاص لأعضاء المجتمع الذين ساهموا في `arabic-educational-skills` وأدوات `youtube-agent-skill` و `youtube-automation-agent`.
