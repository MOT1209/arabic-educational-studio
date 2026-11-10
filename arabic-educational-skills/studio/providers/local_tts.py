"""منفذ النموذج الصوتي المحلي (غير مرتبط بنموذج بعينه).

لا يضم المشروع نموذجاً صوتياً. هذا المنفذ يستدعي أي أمر محلي يحوّل نصاً إلى ملف صوت. يُضبط بمتغير البيئة
`AES_LOCAL_TTS_CMD` (أو `config["cmd"]`) كقالب أمر بلا shell، مثل:

    AES_LOCAL_TTS_CMD='python /path/to/my_tts.py --text-file {text_file} --out {out}'

المتغيران المدعومان في القالب: `{text_file}` ملف UTF-8 فيه النص المشكول، و`{out}` مسار ملف wav المطلوب.
الأمر الصالح: يكتب `{out}` غير فارغ ويرجع 0. لا يُعدّ المزوّد «implemented» إلا إن كان الأمر مضبوطاً وملفه
التنفيذي موجوداً، وتبقى جودة النطق ومعناه من اختصاص المراجعة البشرية (استمع قبل النشر).
"""
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

ENV_CMD = "AES_LOCAL_TTS_CMD"
PLACEHOLDERS = ("{text_file}", "{out}")


class LocalTTSError(RuntimeError):
    pass


class LocalTTSProvider:
    id = "local_tts"

    def __init__(self, config=None):
        config = config or {}
        self.cmd = config.get("cmd") or os.environ.get(ENV_CMD, "")
        self.timeout = float(config.get("timeout", 300))

    def _argv(self, text_file, out):
        argv = shlex.split(self.cmd)
        return [a.replace("{text_file}", str(text_file)).replace("{out}", str(out)) for a in argv]

    def check(self):
        """(ok, سبب). لا يشغّل النموذج: يفحص الضبط والملف التنفيذي فقط."""
        if not self.cmd.strip():
            return False, f"غير مضبوط: عيّن {ENV_CMD} (قالب أمر فيه {{text_file}} و{{out}})"
        try:
            argv = shlex.split(self.cmd)
        except ValueError as e:
            return False, f"قالب أمر غير صالح: {e}"
        if not argv:
            return False, "قالب أمر فارغ"
        if "{out}" not in self.cmd or "{text_file}" not in self.cmd:
            return False, "القالب يجب أن يحوي {text_file} و{out}"
        if shutil.which(argv[0]) is None:
            return False, f"الملف التنفيذي غير موجود: {argv[0]}"
        return True, "مضبوط"

    def synthesize(self, text, output_path):
        ok, why = self.check()
        if not ok:
            raise LocalTTSError(why)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        with tempfile.TemporaryDirectory() as td:
            tf = Path(td) / "text.txt"
            tf.write_text(text, encoding="utf-8")
            try:
                r = subprocess.run(self._argv(tf, out), capture_output=True, text=True, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise LocalTTSError(f"انتهت المهلة ({self.timeout:g}ث)")
        if r.returncode:
            raise LocalTTSError(f"فشل الأمر ({r.returncode}): {(r.stderr or r.stdout)[-300:]}")
        if not out.exists() or out.stat().st_size == 0:
            raise LocalTTSError("الأمر نجح لكنه لم يكتب ملف الصوت")
        return str(out)

    def get_info(self):
        ok, why = self.check()
        return {"provider": self.id, "configured": ok, "detail": why, "offline": True}
