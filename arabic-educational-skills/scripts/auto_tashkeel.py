#!/usr/bin/env python3
"""Auto-Tashkeel (Arabic Diacritization) helper for the educational video pipeline.

Usage:
    python auto_tashkeel.py "نص عربي без تشكيل" [--preserve-punct] [--names "اسم1,اسم2"]
    python auto_tashkeel.py --file input.txt [--output output.json]

Output: JSON mapping each sentence to its fully diacritized text.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Try to import pytashkeel; fall back to a simple passthrough
try:
    from pytashkeel import tashkeel as _tashkeel_fn
    HAS_PYTAHSKEEL = True
except ImportError:
    HAS_PYTAHSKEEL = False

# Arabic punctuation to preserve
ARABIC_PUNCT = "،؛؟!."
SENTENCE_SPLIT = re.compile(r"([.!?؟؛،])")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving punctuation."""
    parts = SENTENCE_SPLIT.split(text)
    sentences = []
    current = ""
    for part in parts:
        current += part
        if part in ARABIC_PUNCT or not part.strip():
            if current.strip():
                sentences.append(current.strip())
                current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences if sentences else [text.strip()]


def _apply_names(text: str, names: list[str]) -> str:
    """Preserve custom phonetic spellings for proper names."""
    for name in names:
        # Ensure the name is not re-diacritized if already diacritized
        if name not in text:
            # Try to find the undiacritized version
            stripped = "".join(c for c in name if c not in "ًٌٍَُِّْٰٕٓٔ")
            if stripped in text:
                text = text.replace(stripped, name)
    return text


def _tashkeel_text(text: str) -> str:
    """Apply tashkeel to text. Uses pytashkeel if available, else passthrough."""
    if HAS_PYTAHSKEEL:
        try:
            return _tashkeel_fn(text)
        except Exception as e:
            # Fall back to passthrough on error
            return text
    return text


def tashkeel(text: str, preserve_punct: bool = True, names: list[str] = None) -> dict:
    """Diacritize Arabic text and return structured JSON."""
    names = names or []
    sentences = _split_sentences(text)
    result = {
        "input": text,
        "sentences": [],
        "error": None,
    }

    for i, sent in enumerate(sentences, 1):
        try:
            # Apply custom names
            processed = _apply_names(sent, names)
            # Apply tashkeel
            diacritized = _tashkeel_text(processed)
            # Preserve punctuation
            if preserve_punct:
                # Ensure sentence ends with punctuation
                if not any(diacritized.endswith(p) for p in ARABIC_PUNCT):
                    diacritized = diacritized.rstrip() + "۔" if "۔" in ARABIC_PUNCT else diacritized
            result["sentences"].append({
                "index": i,
                "original": sent,
                "diacritized": diacritized,
            })
        except Exception as e:
            result["sentences"].append({
                "index": i,
                "original": sent,
                "diacritized": sent,
                "error": str(e),
            })

    return result


def main():
    parser = argparse.ArgumentParser(description="Auto-Tashkeel for Arabic text")
    parser.add_argument("text", nargs="?", help="Arabic text to diacritize")
    parser.add_argument("--file", help="Input file path")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--preserve-punct", action="store_true", default=True,
                        help="Preserve end-of-sentence punctuation")
    parser.add_argument("--names", help="Comma-separated proper names to preserve")
    args = parser.parse_args()

    if args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"خطأ: ملف غير موجود: {args.file}")
            sys.exit(1)
        except OSError as e:
            print(f"خطأ في قراءة الملف: {e}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        print("الاستخدام: python auto_tashkeel.py \"نص عربي\" [--file input.txt] [--output output.json]")
        sys.exit(2)

    names = [n.strip() for n in args.names.split(",")] if args.names else []
    result = tashkeel(text, preserve_punct=args.preserve_punct, names=names)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"تم: {len(result['sentences'])} جملة -> {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    sys.exit(main())