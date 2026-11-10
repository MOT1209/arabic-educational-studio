#!/usr/bin/env python3
"""ربط SILMA TTS (نموذج محلي، فصحى مشكولة، Apache-2.0) بمنفذ الصوت المحلي في الاستوديو.

جُرّب فعلياً على ويندوز (Python 3.11، معالج بلا GPU، --no-nemo) فوُلّد صوت مقبول لدى المستخدم؛ لم يُجرَّب في بيئة التطوير (تنزيل الأوزان محجوب). على CPU التوليد بطيء (دقائق للجملة).

ويندوز بلا WSL (بلا إعادة تشغيل): Python 3.11 في venv ثم
    pip install silma-tts --no-deps
    pip install cached_path click ema_pytorch hydra-core librosa matplotlib "numpy<=1.26.4" pydub safetensors soundfile tomli torch torchaudio torchvision torchdiffeq tqdm transformers unidecode vocos x_transformers catt_tashkeel==1.0.2 gradio
    ثم أضف --no-nemo إلى كل أمر. (طريقة غير مدعومة رسمياً؛ إن فشلت فالحل WSL2.)

التثبيت (جهازك):  apt install ffmpeg && python -m venv v && v/bin/pip install silma-tts
أول تشغيل ينزّل الأوزان من huggingface.co (إنترنت مرة واحدة ثم يعمل محلياً).

وضع السطر الواحد (لـ AES_LOCAL_TTS_CMD):
    export AES_LOCAL_TTS_CMD='/path/v/bin/python /path/scripts/silma_tts_cmd.py --ref-audio my_voice.wav --ref-text "نص ما قلتُه في المرجع" --text-file {text_file} --out {out}'

وضع الدفعة (يحمّل النموذج مرة واحدة لكل الأسطر، وهو الأسرع لفيديو كامل):
    python scripts/silma_tts_cmd.py --ref-audio my_voice.wav --ref-text "..." --batch voice-lines.json --out-dir audio/
    (يتخطى الأسطر الموجودة؛ --force لإعادة التوليد). الملفات باسم المعرّف: audio/<id>.wav

ملاحظات:
- المرجع: صوت لك حق استخدامه، أقل من 8 ثوانٍ، نظيف؛ و--ref-text نصه الحرفي (إن غاب نسخه النموذج آلياً بحمل نموذج إضافي).
- النص المشكول (3 حركات فأكثر) يُستعمل كما هو؛ غير المشكول يُشكَّل آلياً بـCATT (قد يخطئ: لا تعتمده لدروس النحو).
- الحد الأقصى للقطعة نحو 120 حرفاً داخلياً؛ الجمل الأطول تُقسَّم. استمع لكل سطر قبل النشر.
- يلزم الإفصاح للمشاهدين أن الصوت مولَّد بالذكاء الاصطناعي (طلب بطاقة النموذج).
"""
import argparse
import json
import sys
from pathlib import Path


def install_nemo_stub():
    """بديل فارغ لـnemo_text_processing (يحتاج pynini غير المتاح على ويندوز). يعطّل تطبيع الأرقام فقط."""
    import types
    mods = {}
    for name in ("nemo_text_processing", "nemo_text_processing.text_normalization",
                 "nemo_text_processing.text_normalization.normalize"):
        mods[name] = sys.modules.setdefault(name, types.ModuleType(name))

    class Normalizer:
        def __init__(self, *a, **k): pass
        def normalize(self, text, **k): return text
    mods["nemo_text_processing.text_normalization.normalize"].Normalizer = Normalizer


def install_audio_io_patch():
    """torchaudio الحديثة تطلب torchcodec (متعب على ويندوز). نستبدل load/save بـsoundfile (مثبّت أصلاً)."""
    import torch
    import torchaudio
    import soundfile as sf

    def load(path, *a, **k):
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return torch.from_numpy(data.T.copy()), sr

    def save(path, wav, sr, *a, **k):
        arr = wav.detach().cpu().numpy() if hasattr(wav, "detach") else wav
        if arr.ndim == 2:
            arr = arr.T
        sf.write(str(path), arr, sr)

    torchaudio.load, torchaudio.save = load, save


def load_model(device=None, no_nemo=False):
    if no_nemo:
        install_nemo_stub()
    try:
        install_audio_io_patch()
    except ImportError:
        pass
    try:
        from silma_tts.api import SilmaTTS
    except ImportError as e:
        sys.exit(f"تعذّر استيراد silma-tts ({e}). ثبّته: pip install silma-tts، أو على ويندوز أضف --no-nemo (انظر رأس الملف)")
    kw = {"enable_normalizer": False} if no_nemo else {}
    if device:
        kw["device"] = device
    return SilmaTTS(**kw)


def synth(model, text, out, ref_audio, ref_text, speed, seed, no_nemo=False):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    extra = {"normalize_numbers": False} if no_nemo else {}
    model.infer(ref_file=str(ref_audio), ref_text=ref_text or "", gen_text=text.strip(), file_wave=str(out),
                speed=speed, seed=seed, **extra)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"لم يُكتب الصوت: {out}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref-audio", required=True)
    ap.add_argument("--ref-text", default="")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=None, help="ثابت = نفس النطق عند الإعادة")
    ap.add_argument("--no-nemo", action="store_true", help="ويندوز بلا pynini: يعطّل تطبيع الأرقام (اكتب الأرقام حروفاً)")
    ap.add_argument("--device", default=None, help="cuda | cpu | mps (الافتراضي: تلقائي)")
    one = ap.add_argument_group("سطر واحد")
    one.add_argument("--text-file")
    one.add_argument("--out")
    many = ap.add_argument_group("دفعة")
    many.add_argument("--batch", help="voice-lines.json من `plan voice` (حقلا id وtext)")
    many.add_argument("--out-dir")
    many.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    if not Path(a.ref_audio).is_file():
        sys.exit(f"ملف المرجع غير موجود: {a.ref_audio}")
    if bool(a.batch) == bool(a.text_file):
        sys.exit("اختر إما --batch مع --out-dir، أو --text-file مع --out")

    if a.batch:
        if not a.out_dir:
            sys.exit("--batch يحتاج --out-dir")
        lines = json.loads(Path(a.batch).read_text("utf-8"))
        todo = [(l["id"], l["text"], Path(a.out_dir) / f"{l['id']}.wav") for l in lines if l.get("text", "").strip()]
        todo = [t for t in todo if a.force or not t[2].exists()]
        print(f"{len(todo)} سطراً للتوليد من {len(lines)}", flush=True)
        if not todo:
            return 0
        model = load_model(a.device, a.no_nemo)
        failed = []
        for lid, text, out in todo:
            try:
                synth(model, text, out, a.ref_audio, a.ref_text, a.speed, a.seed, a.no_nemo)
                print(f"✓ {lid}", flush=True)
            except Exception as e:                       # سطر فاشل لا يوقف الباقي
                failed.append(lid); print(f"✗ {lid}: {e}", file=sys.stderr, flush=True)
        if failed:
            print(f"فشلت {len(failed)}: {', '.join(failed)}", file=sys.stderr)
            return 1
        return 0

    if not a.out:
        sys.exit("--text-file يحتاج --out")
    text = Path(a.text_file).read_text("utf-8")
    if not text.strip():
        sys.exit("النص فارغ")
    synth(load_model(a.device, a.no_nemo), text, a.out, a.ref_audio, a.ref_text, a.speed, a.seed, a.no_nemo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
