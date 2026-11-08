# Phase 3 — Documentation repair

Scope: `README.md`, `README.en.md`, `README.de.md` audited against the real
directory tree, the real package scripts, and commands that were actually run.

## 1. Defects found and fixed

| ID | File(s) | Defect | Evidence | Status |
| --- | --- | --- | --- | --- |
| D1 | all three | Tree root named `AI vedio/`, and listed `exports/` at the root | `ls` shows `arabic-educational-studio`-style root with no `exports/` | Fixed |
| D2 | all three | Tree omitted `tools/`, `.github/workflows/ci.yml`, and the real `projects/<video>/exports/` | `find -maxdepth 2` | Fixed |
| D3 | EN, DE | Malformed box drawing (`├ ├──`, `└ └──`) | raw file | Fixed |
| D4 | DE | Broken heading `## �1 Organisatorische Struktur` | raw file | Fixed |
| D5 | EN, DE | Stray `</content>` at end of file, rendered as text | `grep '</content>'` | Fixed |
| D6 | DE | YouTube link had an extra letter: `…%D8%A7%D9%84%D8%B9%D8%B1%D8%A8**%D9%86**%D9%8A%D8%A9` (العربنية) | byte comparison against `README.md` | Fixed |
| D7 | EN, DE | `cd AI\ vedio` — a Windows-escaped path that fails on Linux and does not match the clone directory | text | Fixed |
| D8 | EN, DE | `<repository-url>` placeholder instead of the real clone URL | text | Fixed |
| D9 | EN, DE | Install order impossible: `npm run walkthrough` ran before any dependency install, and `npm install`/`npm ci` was never mentioned | `package.json` scripts + `package-lock.json` present | Fixed |
| D10 | all three | No environment variables documented | `.env.example` has ~90 | Fixed |
| D11 | all three | No Windows instructions; hidden Linux-only assumptions | text | Fixed |
| D12 | all three | Scripts table listed 4 of the 10 scripts in `scripts/`, and never mentioned `python -m studio` | `ls scripts`, `python -m studio --help` | Fixed |
| D13 | all three | No test commands and no description of CI | `.github/workflows/ci.yml` | Fixed |
| D14 | `scripts/doctor.py` | The documented command aborted with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'` on a Windows console (cp1256) | traceback captured before the fix | Fixed |

D14 was a code change and not a documentation one. It was included because the
Phase 3 acceptance bar is "the documented commands work", and `doctor.py` was
the documented environment check. The change is three lines: reconfigure
`sys.stdout` to UTF-8 with `errors="replace"`, guarded for platforms without
`reconfigure`.

A defect I introduced myself and caught during verification is recorded too:
the first draft of all three files said "every script accepts `--help`", which
is false for `validate_brief.py`, `voice_pack.py` and `gen_srt.py` — they take a
positional path and treat `--help` as that path. The corrected text names which
scripts support `--help` and shows the positional usage instead.

## 2. Verification (actual output)

Every path printed in the three trees, and every file the docs link to:

```
missing=0        # 30 paths checked: skills subdirs, youtube/*, tiktok/*, tools/*, .env.example, docs/providers.md, thumbnail, audit reports
```

Every script named in the tables exists (`10/10`), and `--help` was run on each:

```
0 scripts/auto_tashkeel.py      0 scripts/check_output.py     0 scripts/doctor.py
1 scripts/gen_srt.py            0 scripts/mux_audio.py        0 scripts/retime_from_audio.py
1 scripts/validate_brief.py     0 scripts/validate_script.py   1 scripts/voice_pack.py
```

Exit 1 for the three positional scripts is the finding behind the corrected
wording, not a failure of the documented usage.

The environment check, run exactly as documented and without any helper variable:

```
$ python arabic-educational-skills/scripts/doctor.py
✓ Python ≥ 3.9        ✓ ffmpeg           ✓ ffprobe        ✓ jsonschema
✓ playwright (Python) ✓ متصفح Chromium    ✓ خطوط القالب (2)
✓ Node.js ≥ 18 (v24.19.0)                ✓ اعتماديات Remotion
المحرك جاهز للتصيير
exit=0
```

`python -m studio --help` exits 0 and lists `new, status, step, submit, approve,
reject, modify, regenerate, rewind, compare, resume, verify, interview, styles,
providers, lesson, plan, review, assets, subtitles`.

Documented test command, per file (the aggregate run is covered by CI):

```
tests/test_core.py:    22 passed  in 37.33s
tests/test_studio.py:  43 passed, 1 skipped  in 80.35s
tests/test_phase1.py::test_review_sheet_roundtrip: 1 passed, 1 skipped in 28.88s
111 tests collected in 2.09s
```

Structural checks: code fences even in all three (26/26/26); no `</content>`, no
U+FFFD, no `AI\ vedio`; the YouTube channel URL is now byte-identical in all
three files; the 12 German section headings render correctly.

## 3. Limitations

- The full local `python -m pytest tests -q` did not finish inside a 5 minute
  budget on Windows with Python 3.14; it is slow rather than stuck, since the
  individual files above pass. CI runs this exact command on Ubuntu 24.04 with
  Python 3.12 and it is green (run 42465521319), so CI is the arbiter for it.
- The `[xlsx]` variant of `test_review_sheet_roundtrip` is skipped locally
  because `openpyxl` is not installed here; CI installs it and does not skip.
- No claim in this report comes from a command that was not run.

## 4. Left open (not part of this phase)

- `TIK TOK/` and `YOU TUBE/` are legacy directories outside the pipeline; the
  README now says so instead of silently omitting them. Consolidating them is
  Phase 4 (project boundaries) work.
- `validate_brief.py`, `voice_pack.py` and `gen_srt.py` do not support `--help`
  and crash with a traceback when called with no arguments. Documented
  accurately rather than changed, since fixing their argument handling is not a
  documentation repair.
