"""محرك التوقيت: تقدير زمن الكلام والوقفات، وضبط المدة الكلية ضمن سماحية صريحة."""

# كلمات في الثانية: (طبيعي، بطيء)
WPS = {"child": (1.7, 0.8), "preteen": (2.0, 1.0), "teen": (2.4, 1.3), "adult": (2.6, 1.5)}
MIN_LINE = 1.3
DEFAULT_TOLERANCE = 0.10


def speech_seconds(text, age="child", delivery="natural", lang="ar"):
    words = max(1, len(text.split()))
    nat, slow = WPS[age]
    wps = slow if delivery == "slow" else nat
    if lang != "ar":
        wps *= 1.35  # الإنجليزية أسرع في الكلمات المنطوقة لكل ثانية
    return max(MIN_LINE, round(words / wps + 0.35, 2))


def repeat_pause(utterance_seconds, age="child"):
    """وقفة تكرار الطفل: مرة وربع زمن النطق + ثانية، بحد أقصى 6 ث (أقل للأكبر سناً)."""
    k = {"child": 1.25, "preteen": 1.0, "teen": 0.7, "adult": 0.4}[age]
    return round(min(6.0, utterance_seconds * k + (1.0 if age in ("child", "preteen") else 0.4)), 2)


def fit_report(total, target, tolerance=DEFAULT_TOLERANCE):
    lo, hi = target * (1 - tolerance), target * (1 + tolerance)
    return {"total_seconds": round(total, 1), "target_seconds": target, "tolerance": tolerance,
            "within_tolerance": lo <= total <= hi, "deviation_pct": round((total - target) / target * 100, 1)}
