# بنية الاستوديو 3.0

```
studio/
  core/       schema (محقق JSON مدمج) · workflow (12 مرحلة) · state (Project) · approvals · cost · orchestrator
  agents/     interviewer · creative_director · research · scriptwriter · storyboard · subtitles · qa
  engines/    script_engine (سرعة الكلام، توقيت، سماحية المدة)
  systems/    arabic_language · kids_learning · style_manager · provider_manager · asset_manager
  pipeline.py يربط الوكلاء بالمراحل    cli.py / __main__.py
engine/       محرك التصيير: HTML/SVG ← Playwright ← FFmpeg (حتمي: renderAt(t))
schemas/      عقود JSON    tests/   pytest
```

## عقد المرحلة
`Orchestrator.run_stage(id)`: يجمع مدخلات المراحل المعتمدة السابقة ← يستدعي الوكيل ← يتحقق بـschema المرحلة ← يحفظ `artifacts/<stage>/rNNN.json` (لا يُستبدل) ← الحالة `awaiting_approval` أو `done`.
- الوكيل `FuncAgent` حتمي؛ `HostTask` يطلب نتيجة من النموذج المضيف (`awaiting_output`).
- خطأ `NonRetriable` (مثل فشل تصيير) يوقف المرحلة `failed` بلا إعادة محاولة؛ غيره يُعاد حتى حد.
- تعديل مرحلة مُعتمدة يُبطل اللاحقة (`invalidated`).

## الموافقات
`approvals.jsonl` مُلحَق فقط، كل سطر يحمل هاش السطر السابق: يُكتشف التعديل والحذف والترتيب بـ`verify()`. كل سجل: مشروع، مرحلة، قرار، وقت، مراجعة، تعليق، معتمِد. **لا يمنع** من يملك الملفات من إعادة كتابة السلسلة كلها، ولا يثبت أن المعتمِد إنسان.

## ما يفحصه الكود وما لا
| يفحصه الكود | لا يفحصه (توقيع بشري) |
|---|---|
| موضع الحرف، شكله، اتصاله، ألف/مقصورة، الشدة، التشكيل البنيوي | معنى الكلمة، نطقها، ملاءمتها للعمر |
| المدة وسماحيتها، سرعة القراءة، تداخل الأسطر | جودة الشرح التربوي والتصميم |
| بصمات الملفات والتلاعب بها | صحة الأصول المرخّصة |

## التوسعة
مزوّد جديد: سجّله في `provider_manager` بحالة `implemented` مع تنفيذ `call` فعلي، وإلا يبقى `not_implemented`. نمط جديد: `StyleManager.create`؛ لا يصير native إلا بقالب مشهد في `engine/`. مادة جديدة في استوديو الأطفال: أضف وحدة تنتج `letter_lesson`-like ثم محوّلاً إلى master-script.
