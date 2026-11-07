# Tools (الأدوات المضافة)

تم إضافة 3 مستودعات GitHub إلى المشروع:

## 1. elephant-goldfish-model (EGM)
- المسار: `tools/elephant-goldfish-model/`
- الوصف: إضافة (plugin) لـ Claude Code/Codex/Gemini لتصميم ومراجعة البرمجيات (Elephant يحتفظ بالسياق، Goldfish يراجع بعيون جديدة).
- التثبيت: `claude plugin marketplace add google/elephant-goldfish-model` (في Claude Code).
- Skills منسوخة إلى `.claude/skills/egm-*`.

## 2. youtube-agent-skill
- المسار: `tools/youtube-agent-skill/`
- الوصف: 11 مهارة Claude لإدارة قناة YouTube (scripts, hooks, packaging, retention, shorts, viral, seo, chapters, audit).
- Skills منسوخة إلى `.claude/skills/yt-*` (متاحة الآن في OpenCode).
- الأدوات Python: `skills/yt-script/hookscore.py`, `yt-package/title.py`, `yt-edit/deadair.py`, `yt-chapters/chapters.py`, `yt-retention/retention.py`, `yt-viral/swipe.py`.

## 3. youtube-automation-agent
- المسار: `tools/youtube-automation-agent/`
- الوصف: وكيل AI مُستضاف ذاتياً (self-hosted) يُشغّل قناة YouTube من البداية للنهاية (بحث → سيناريو → تعليق صوتي → MP4 → SEO → نشر بعد موافقة).
- node_modules مثبتة. `.env` تم إنشاؤه من `.env.example` (أضف مفاتيح API).
- تشغيل: `npm run walkthrough` (إعداد) ثم `npm start` (http://localhost:3456).
- ملاحظة: `npx playwright install chromium` (لعرض slideshow videos).

## ملاحظات
- المستودعات مستنسخة (git clone). لتحديث: `cd tools/<name> && git pull`.
- `.gitignore` should ignore `node_modules/` and `.env` (أضف يدوياً إن لزم).
