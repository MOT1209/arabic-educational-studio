#!/usr/bin/env python3
"""توليد صوت خطة كاملة تلقائياً بـ SILMA على جهازك (أمر واحد).

    python scripts/voice_local.py plan.json            # يقرأ الإعدادات من voice.config.json
    python scripts/voice_local.py plan.json --ref-audio ref.wav --ref-text "..."

الإعدادات تُحفظ مرة واحدة في voice.config.json (بجانب الخطة أو في مجلد المهارة):
    {"ref_audio": "C:/Users/aihmo/slima/ref.wav", "ref_text": "نص المرجع الحرفي", "speed": 1.0, "seed": 7}

يستخرج أسطر الخطة، ويولّد لكل سطر audio/<id>.wav (يتخطى الموجود: أعد التشغيل لاستكمال ما انقطع)،
ثم يطبع أمر التصيير. يعمل داخل venv فيه silma-tts (انظر رأس silma_tts_cmd.py)."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))


def load_config(plan_path, explicit=None):
    for p in ([Path(explicit)] if explicit else []) + [plan_path.parent / "voice.config.json", ROOT / "voice.config.json"]:
        if p.is_file():
            return json.loads(p.read_text("utf-8")), p
    return {}, None


def needs_no_nemo():
    try:
        import nemo_text_processing  # noqa: F401
        return False
    except Exception:
        return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--config")
    ap.add_argument("--ref-audio")
    ap.add_argument("--ref-text")
    ap.add_argument("--out-dir")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--device")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    plan_path = Path(a.plan).resolve()
    cfg, cfg_path = load_config(plan_path, a.config)
    ref_audio = a.ref_audio or cfg.get("ref_audio")
    ref_text = a.ref_text if a.ref_text is not None else cfg.get("ref_text", "")
    if not ref_audio:
        sys.exit("لا يوجد صوت مرجعي: مرّره بـ --ref-audio أو ضعه في voice.config.json (ref_audio, ref_text)")
    if not Path(ref_audio).is_file():
        sys.exit(f"ملف المرجع غير موجود: {ref_audio}")
    speed = a.speed if a.speed is not None else cfg.get("speed", 1.0)
    seed = a.seed if a.seed is not None else cfg.get("seed")

    from studio.lesson_plan import plan as LP
    plan = LP.load(plan_path)
    E, W = LP.validate(plan)
    if E:
        sys.exit("الخطة غير صالحة:\n- " + "\n- ".join(E))
    lines = LP.voice_lines(plan)
    out_dir = Path(a.out_dir or plan_path.parent / "audio")
    out_dir.mkdir(parents=True, exist_ok=True)
    jl = out_dir / "voice-lines.json"
    jl.write_text(json.dumps(lines, ensure_ascii=False, indent=2), "utf-8")
    done = sum(1 for l in lines if (out_dir / f"{l['id']}.wav").exists())
    print(f"{len(lines)} سطراً ({done} جاهز مسبقاً). الإعدادات: {cfg_path or 'سطر الأوامر'}", flush=True)

    import silma_tts_cmd as S
    argv2 = ["--ref-audio", str(ref_audio), "--ref-text", ref_text, "--speed", str(speed),
             "--batch", str(jl), "--out-dir", str(out_dir)]
    if seed is not None:
        argv2 += ["--seed", str(seed)]
    if a.device:
        argv2 += ["--device", a.device]
    if a.force:
        argv2.append("--force")
    if needs_no_nemo():
        argv2.append("--no-nemo")
    t0 = time.time()
    rc = S.main(argv2)
    print(f"انتهى في {time.time() - t0:.0f} ثانية (رمز {rc}).", flush=True)
    if rc == 0:
        print(f"\nالتصيير:\n  python -m studio plan render {plan_path} --audio {out_dir} --out out/")
        print("أو اضغط مجلد audio وأرسله إلى Claude ليصيّر الفيديو.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
