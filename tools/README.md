# الأدوات (tools/)

ثلاث أدوات مُضمَّنة (vendored) داخل هذا المستودع. ليست مستودعات فرعية: لا يوجد `.git` داخل أي
منها، وأي أمر git يُنفَّذ هنا يخصّ المستودع الأم. المصدر الحقيقي هو مجلد الأداة نفسه، والتحديث
من المنبع يدوي (نسخ ثم مراجعة الفرق)، وليس `git pull`.

| الأداة | المسار | البيئة | المدخل | ما تنتجه |
|---|---|---|---|---|
| Elephant-Goldfish Model (EGM) | `elephant-goldfish-model/` | Python ≥ 3.10، Node 22 | `pytest tests/unit`، و`cd site && npm ci` للموقع | تقارير مراجعة، حزم تشغيل مولّدة في `distributions/`، موقع في `site/dist/` |
| YouTube Agent Skill (YAS) | `youtube-agent-skill/` | Python 3 (stdlib فقط) | `python3 skills/<skill>/*.py` | نصوص Markdown / قائمة مونتاج / فصول؛ لا تنشر شيئاً |
| YouTube Automation Agent (YTA) | `youtube-automation-agent/` | Node ≥ 18.17، ffmpeg | `npm ci` ثم `npm start` (127.0.0.1:3456)، `npm test`، `npm run lint` | `data/`، `uploads/`، سجلات، ونشر YouTube بعد الموافقة |

روابط المنبع: EGM `google/elephant-goldfish-model`، YAS `Jakeschincariol/youtube-agent-skill`.
YTA لا يعلن رابط مستودع في `package.json`.

## النسخ في `.claude/skills/`

مجلدات `yt-*` و`egm-*` في `.claude/skills/` نسخ من `tools/*/skills/` (متطابقة بايتاً بايتاً وقت
الكتابة). عند التعديل: عدّل المصدر أولاً ثم انسخ؛ لا تعدّل النسخة وحدها. لا تنسخ `__pycache__/`.

## التثبيت والتشغيل

```bash
# EGM — اختبارات الوحدة ثم الموقع
cd tools/elephant-goldfish-model
python -m pip install --upgrade "pip>=25.1" && python -m pip install --group test
pytest tests/unit
cd site && npm ci && npm test && npm run check && npm run build

# YAS — لا تثبيت (stdlib)، الأدوات تُشغَّل من مجلد المهارة
cd tools/youtube-agent-skill
python3 skills/yt-script/hookscore.py --hook "خطاف تجريبي"

# YTA — الاعتماديات، متصفح Playwright، ثم المعالج
cd tools/youtube-automation-agent
npm ci
npx playwright install chromium
npm run walkthrough   # ينشئ .env وconfig/credentials.json محلياً
npm start
```

`.env` و`config/credentials.json` و`data/` و`uploads/` محلية ومتجاهَلة في git؛ لا تُرفع.

## الحدود والعقود

خريطة الحدود الكاملة — من يملك أي مسار، الاعتماديات المشتركة والمكررة، وعقود التكامل C1–C7 —
في [`../PHASE4_BOUNDARIES_AUDIT.md`](../PHASE4_BOUNDARIES_AUDIT.md).
