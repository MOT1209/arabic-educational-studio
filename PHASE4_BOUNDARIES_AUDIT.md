# Phase 4 — Project boundaries, dependency overlap, integration contracts

Scope: the four independent projects in this repository (`arabic-educational-skills`
and the three under `tools/`), plus the non-code content trees. Read from the
tree, the manifests, the lockfiles and the CI workflow; no file outside the
repository was consulted. No `.env` or credential file contents were read — only
variable names and counts.

The deliverable is a boundary map, an overlap analysis, and six contracts
(C1–C6) plus one explicitly missing contract (C7). Ten defects were found; three
were fixed in this phase and the rest need a decision or a change outside it.

## 1. Boundary map

Every project owns its install root and its lockfile. There is no workspace, no
root `package.json`, and no shared Python package.

| Project | Runtime | Owned root | Entry points (verified) | Writes | Consumes | CI job |
| --- | --- | --- | --- | --- | --- | --- |
| **AES** — Arabic Educational Skills | Python ≥ 3.9, Node ≥ 18.17 (Remotion 4.0.541) | `arabic-educational-skills/` | `python -m studio …`, `python engine/build.py`, `python scripts/doctor.py`, `node remotion/render.mjs` (called by `studio/lesson_plan/render.py`) | `projects/<name>/` (`project.json`, `artifacts/`, `approvals.jsonl`, `tasks/`, `exports/`, `subtitles/`, `build/`) and `<out>/<slug>-<fmt>.mp4/.srt` | `ffmpeg`/`ffprobe` on `PATH`; optional `jsonschema`, `Pillow`, `numpy`; Chromium via `AES_CHROME` or Playwright | `arabic-educational-skills` |
| **YTA** — YouTube Automation Agent | Node ≥ 18.17, ffmpeg | `tools/youtube-automation-agent/` | `npm start` (Express), `npm test`, `npm run lint`, `npm run agent:*`, `npm run walkthrough` | `data/` (SQLite `youtube_automation.db`), `uploads/`, `logs/`, `reports/`, `temp/`, OAuth token | `.env` (85 declared variables), `config/credentials.json` (mode 0600), YouTube Data API, `ffmpeg` (`FFMPEG_PATH` → `ffmpeg-static` → `PATH`), Playwright Chromium | `youtube-automation-agent` |
| **YAS** — YouTube Agent Skill | Python 3, standard library only | `tools/youtube-agent-skill/` | `python3 skills/yt-*/{hookscore,title,deadair,chapters,retention,swipe}.py` plus the `SKILL.md` prompts | Only files the user asks for (scripts, EDLs, chapters, text) | Transcripts, `.srt`, `.csv`, `.json` inputs; `~/.claude/youtube/voice.md` | `youtube-agent-skill` (byte-compile only) |
| **EGM** — Elephant-Goldfish Model | Python ≥ 3.10, Node 22 | `tools/elephant-goldfish-model/` | `pytest tests/unit`, `cd site && npm test|check|build`, `python scripts/prepare_release.py` | Review reports in the working directory, `distributions/` (generated), `site/dist/` | `pyproject.toml` `[dependency-groups] test` (pytest 8.3.5, pyyaml 6.0.2); Node 22 for the workflow JavaScript tests | `elephant-goldfish-model`, `elephant-goldfish-site` |

Non-code trees, and which project owns them:

| Tree | Contents | Owner | Note |
| --- | --- | --- | --- |
| `projects/` | `project-01-inna`, `project-02-anna`, `project-03-lakinna` | AES (legacy engine layout) | One render output, `projects/project-01-inna/exports/scene_01.mp4`, is tracked even though `**/exports/` is ignored (D6). |
| `youtube/` | `long-form/`, `shorts/`, `metadata/`, `thumbnails/` | Publishing (human) | 3 `.mp4` and 1 `.jpg` are tracked even though `*.mp4` is ignored (D6). `metadata/youtube-metadata.md` is hand-written. |
| `tiktok/` | `shorts/`, `metadata/`, `covers/` | Publishing (human) | `metadata/tiktok-metadata-01.md` is hand-written. |
| `assets/` | `branding/`, `characters/` | Shared media | Not read by any build step. |
| `.claude/skills/` | 11 `yt-*` + 7 `egm-*` directories | Mirrors YAS and EGM | Byte-identical copies, verified; see C4. |
| `TIK TOK/`, `YOU TUBE/shorts y` | Empty directories | None | Legacy leftovers, untracked (D7). |

**Boundary rule.** A project may not import from another project's source tree.
Shared code does not live in a fifth location: the only executable sharing in the
repository is the skill mirror and the host toolchain.

## 2. What actually couples the projects

- **Zero code imports across projects.** `require('../../…')` has 0 matches; no
  Python file under `arabic-educational-skills/` imports from `tools/`, and vice
  versa. The 68 textual matches for project names are in documentation, CI, and
  the committed growth reports.
- **Shared host prerequisites**, not shared packages: Python, Node, `ffmpeg` +
  `ffprobe`, and a local Chromium. `ffmpeg` has two different resolution policies
  (AES calls `ffmpeg` on `PATH`; YTA checks `FFMPEG_PATH`, then `ffmpeg-static`,
  then `PATH`), so `PATH` is the only portable assumption.
- **Shared repository infrastructure**: the root `ci.yml`, the root `.gitignore`,
  `LICENSE`, and the `.claude/skills` mirror.
- **No shared state**: YTA's database, credentials and uploads live under its own
  root; AES state lives in `projects/<name>/`. Neither reads the other's files.

The projects are therefore siblings with a one-way dependency on the repository
(Node/Python toolchain + CI), not a pipeline. Any future handoff must be defined
explicitly rather than assumed (see C7).

## 3. Dependency overlap

Verified by diffing every dependency name across the four `package.json` files:

| Dependency | Where declared | Version | Verdict |
| --- | --- | --- | --- |
| npm packages | `remotion/`, YTA, EGM `site/`, EGM `tests/integration/opencode-ci/` | — | **Zero shared package names across all four manifests.** No hoisting is possible or needed. |
| `pytest` | AES (CI command, unpinned), EGM (`pyproject.toml`, `8.3.5`) | Two declarations, two pinning policies | Duplicate *declaration*, not a shared import. AES has no Python manifest at all (D2). |
| `pyyaml` | AES (CI command), EGM (`6.0.2`) | AES installed it but imports it nowhere | Fixed: removed from the AES CI install (D3). |
| `jsonschema`, `Pillow`, `numpy` | AES only | Unpinned in CI | Single-project optional deps; no overlap. |
| Browser automation | Remotion 4.0.541 (own Chromium), YTA `playwright ^1.54.2`, EGM site `puppeteer-core 25.16.0` | Three stacks | Inherent: each is pinned by its host tool. Contract is "one local Chromium is available", not a shared package. |
| `ffmpeg` | AES (Python `subprocess`), YTA (`utils/ffmpeg.js`) | Two wrappers, two lookup orders | Inherent. Contract is the binary on `PATH` plus the documented override variables. |
| Skill directories | `tools/youtube-agent-skill/skills/yt-*` and `tools/elephant-goldfish-model/skills/egm-*` | Mirrored into `.claude/skills/` | Duplicated by design; currently byte-identical (C4). No sync check (D8). |
| EGM runtime files | `skills/`, `agents/`, `resources/`, `docs/`, `plugin.json` → `distributions/` | 66 tracked files | Duplicated by design; generated by `scripts/pack_plugin.py` and `scripts/prepare_release.py` (C5). Never hand-edited. |

There is no dependency that can be deduplicated by hoisting without introducing
a workspace, which the repository deliberately does not have.

## 4. Integration contracts (normative)

### C1 — Lesson plan → Remotion (AES internal, enforced by code)

- **Producer**: `studio/lesson_plan/plan.py::render_props()` → `render.py::prepare()`.
- **Consumer**: `remotion/render.mjs` (ESM, `node`).
- **Call**: `node render.mjs <props.json> <out> <publicDir> [--composition ID] [--still F1,F2] [--concurrency N]`.
- **Exit codes**: `2` for missing arguments (usage), non-zero on render failure.
  The Python caller raises `RenderError` with the last 3000 characters of stderr/stdout.
- **Props**: `format` (`16:9|9:16|1:1`) selects the composition
  (`Lesson-16x9|Lesson-9x16|Lesson-1x1`); `width`/`height`/`durationInFrames`/`fps` (30);
  `audio[].src` is `audio/<filename>` relative to `publicDir`; `blocks[]` and
  `captions[]` are frame-anchored.
- **`publicDir` layout**: `fonts/*.woff2`, `audio/`, `images/`.
- **Environment**: `AES_CHROME` optionally points at a browser executable;
  otherwise Remotion resolves its own.
- **Stability signal**: `PLAN_VERSION = "1.0"` in `plan.py` gates input shape.
  The props object itself is unversioned (D5).

### C2 — Render deliverables (AES output)

- **Naming**: `<out>/<slug>-<16x9|9x16|1x1>.mp4` and `.srt`; stills
  `<slug>-<tag>_<frame>.png`; work files in `<out>/.work/` (`props-<fmt>.json`, `public/`).
- **Report**: `render()` returns `{warnings[], outputs[{format, video, srt, seconds, has_audio, technical_check, check_log}], missing_audio[]}`.
- **Consumer**: a human, who copies files into `youtube/` or `tiktok/` (C7). No
  automated consumer exists.

### C3 — YTA runtime (HTTP, storage, environment)

- **Binding**: `HOST` (default `127.0.0.1`) and `PORT`, exposed by
  `index.js`; loopback by default.
- **Health**: `GET /health` is unauthenticated and returns
  `{status: "healthy"|"setup_required", version, initialized, setupRequired, agents[], uptime, timestamp}`.
- **Auth**: when `API_KEY` is set, mutating routes require the `x-api-key` header;
  a mismatch returns `401 {success:false, error:"Unauthorized"}`. When `API_KEY`
  is unset the guard passes through — documented debt from Phase 2 (D10).
- **Storage**: `data/` (SQLite `youtube_automation.db`), `uploads/`, `logs/`,
  `config/credentials.json` at mode `0600`. All local and git-ignored.
- **Environment**: `tools/youtube-automation-agent/.env.example` is the single
  source of truth. Code reads 64 variables; the file declares 86.
  `ELEVENLABS_TTS_MODEL` was read but undocumented — fixed in this phase (D1).

### C4 — Skill packs (YAS and EGM)

- **Frontmatter**: `SKILL.md` requires `name` and `description`; the directory
  name must equal `name`. EGM additionally uses `license` and
  `disable-model-invocation`.
- **YAS tools**: Python 3 standard library only, run from the skill directory,
  file path or flag input (`--hook`, `--title`/`--thumb`, transcript path).
- **Mirror**: `.claude/skills/<name>` must stay byte-identical to
  `tools/*/skills/<name>`. EGM mirrors test fixtures (`TEST.md`,
  `test_scenarios.yaml`) too; YAS mirrors exclude only untracked `__pycache__/`.
  There is no automated drift check (D8); edit the source, then copy.

### C5 — EGM packaging (release artifacts)

- **Version lockstep**: `plugin.json`, `.claude-plugin/plugin.json`, and
  `.codex-plugin/plugin.json` must all equal the release tag
  (`scripts/prepare_release.py::version_for_tag`).
- **Whitelist**: `scripts/pack_plugin.py` copies only `SHARED` + host files and
  refuses hooks, MCP/app dependencies, symlinks, and unbundled manifest
  references.
- **`distributions/` is generated**, never hand-edited. It excludes `TEST.md`
  and `test_scenarios.yaml` by design.

### C6 — Repository CI

- Five project jobs plus the `ci` gate; the gate fails on any non-`success`
  result, including `skipped`. Each job sets its own `working-directory`.
- Four lockfiles exist (`remotion/`, YTA, EGM `site/`, EGM `opencode-ci/`); CI
  installs with `npm ci` only from those directories.
- **Adding a project requires**: its own install root and lockfile, a CI job, a
  new entry in the `ci` job's `needs`, a `.gitignore` rule for its outputs, and a
  README row. No root-level `npm install` is ever valid.

### C7 — AES → publishing (missing; do not assume it exists)

Today the handoff is manual and unversioned:

- AES writes `<out>/<slug>-<fmt>.mp4` + `.srt`; a human copies them to
  `youtube/long-form/`, `youtube/shorts/`, or `tiktok/shorts/`.
- Metadata is hand-written Markdown (`youtube/metadata/youtube-metadata.md`,
  `tiktok/metadata/tiktok-metadata-01.md`).
- Neither YTA nor YAS reads those files. YTA generates and publishes its own
  content; YAS writes text for a human to upload.

If this becomes automated, the contract needs a versioned sidecar (video, SRT,
title/description/tags, aspect, disclosure) rather than folder conventions.
That is a new feature and is out of scope for this phase.

## 5. Defects

| ID | Defect | Evidence | Status |
| --- | --- | --- | --- |
| D1 | `ELEVENLABS_TTS_MODEL` is read by `utils/ai-video-generator.js` but absent from `.env.example` (the declared SSoT) | env-drift scan: 64 used, 85 declared, 1 missing | **Fixed** — documented as an optional override, default `eleven_v3` |
| D2 | `arabic-educational-skills` has no Python dependency manifest; its test dependencies exist only in the CI command, unpinned | no `requirements*.txt`/`pyproject.toml`; CI installs inline | Open — a `requirements-dev.txt` plus a CI `-r` would remove the drift, but it changes the install flow |
| D3 | AES CI installed `pyyaml`, which no AES Python file imports | `grep -rn "yaml" arabic-educational-skills --include=*.py` → no matches | **Fixed** — removed from the CI install |
| D4 | `tools/README.md` claimed the tools' `node_modules` were installed and `.env` created, and told readers to update with `git pull` from a directory with no `.git` | file content vs `find tools -name .git` and the real tree | **Fixed** — rewritten as a boundary map |
| D5 | The Remotion props JSON has no version field; only `PLAN_VERSION` gates the plan | `plan.render_props()` output keys | Open — touches both sides of C1 |
| D6 | Two deliverable trees with conflicting ignore rules: `youtube/*.mp4` are tracked despite `*.mp4`; `projects/project-01-inna/exports/scene_01.mp4` is tracked despite `**/exports/` | `git ls-files` | Open — these are user artifacts; deleting or un-tracking needs a decision |
| D7 | Empty legacy directories `TIK TOK/` and `YOU TUBE/shorts y` remain from the pre-`projects/` layout | `find` shows no files; `git ls-files` shows none | Open — deletion needs a decision |
| D8 | `.claude/skills/` mirror can drift silently; no CI check compares it with `tools/*/skills/` | manual `diff -rq` passes today | Open — a CI diff job is the fix |
| D9 | YAS has no test suite; CI only byte-compiles `skills/` | `ci.yml` `youtube-agent-skill` job | Open — recorded, not pretended |
| D10 | YTA auth fails open when `API_KEY` is unset, and several `GET /api/*` routes are unauthenticated | `index.js::requireAPIKey()`; route table | Open from Phase 2 — needs the `test.js` assertion updated with the behavior change |

## 6. Verification (actual output)

```
$ node -e '<compare dependency names across the 4 package.json files>'
  → prints 4 manifests (6 / 22 / 12 / 1 deps), no overlap section
$ node -e '<count process.env vs .env.example>'
  → before fix: used: 64 declared: 85 missing: 1 (ELEVENLABS_TTS_MODEL)
  → after fix:  used: 64 declared: 86 missing: 0
$ for n in yt-* egm-*; do diff -rq .claude/skills/$n tools/*/skills/$n; done
  → identical; only "Only in tools/...: __pycache__" for the six yt skills with Python tools
$ git ls-files "youtube/*" "tiktok/*"
  → 6 files (3 mp4, 1 jpg, 2 md)
$ git ls-files | grep -c "exports/"
  → 1
$ find . -name package-lock.json -not -path "*/node_modules/*"
  → 4 lockfiles
$ grep -rn "require('../../" --include=*.js
  → 0 matches
$ grep -rn "import yaml\|from yaml" arabic-educational-skills --include=*.py
  → 0 matches
```

Not run: local full test suites (the Windows/Node environment cannot complete
`npm ci` for YTA, and the AES suite exceeds five minutes locally). CI is the
arbiter; it must run after this phase is pushed.

## 7. Decisions left open

1. D2: add `requirements-dev.txt` for AES and have CI install from it.
2. D5: version the Remotion props object (e.g. `"props_version": "1.0"`) and
   reject unknown major versions in `render.mjs`.
3. D6/D7: untrack the stray mp4s and delete the two empty legacy directories.
4. D8: add a CI job that diffs `.claude/skills/` against `tools/*/skills/`.
5. D10: close the Phase 2 auth findings (fail-open `API_KEY`, unauthenticated GETs).
