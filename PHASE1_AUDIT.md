# Phase 1 — CI/CD Stabilization Report

Scope: Phase 1 only. Phases 2–5 have not been started, because the master prompt
requires Phase 1 acceptance before proceeding.

Every result below was executed in this working tree. Nothing is inferred.

---

## 1. What was wrong

| Finding | Evidence |
| --- | --- |
| Repository had **no** CI at all | `git ls-files \| grep '^\.github'` returned nothing; `glob .github/workflows/*` = 0 files |
| Vendored workflow targeted a branch that does not exist | `tools/youtube-automation-agent/.github/workflows/ci.yml` triggered on `master`; `git branch -a` shows only `main` |
| No per-project test entry points existed | 4 independent `package.json` projects plus 3 Python trees, none covered by a workflow |
| A real renderer bug was hidden by the untested suite | `test_stills_render_all_formats` failed with `Could not find composition with ID Lesson. Available compositions: Lesson-16x9, Lesson-9x16, Lesson-1x1` |

Note: nested `.github/` directories under `tools/` are inert on GitHub — only the
repository-root `.github/workflows/` runs. The vendored `master` trigger was
therefore dead configuration, which is why the bug was invisible.

## 2. Changes (3 files, 2 of them one-line-scale)

1. **`.github/workflows/ci.yml`** (new) — one job per independent project plus a
   required-result gate:
   - `arabic-educational-skills` — Ubuntu, Python 3.12, ffmpeg, Remotion `npm ci`,
     `npx remotion browser ensure`, `pytest tests`
   - `youtube-automation-agent` — Node 20 (matches its own `engines`), `npm ci`,
     `npm run lint`, `npm test`
   - `youtube-agent-skill` — Python 3.12, `python -m compileall -q skills`
   - `elephant-goldfish-model` — Python 3.12 + Node 22, `pip install --group test`,
     `pytest tests/unit`
   - `elephant-goldfish-site` — Node 22, `npm ci`, `npm test`, `npm run check`, `npm run build`
   - `ci` — `if: always()`, `needs:` all five, emits `::error` annotations naming
     the failed project and linking the run
   - Triggers: `push` on `main`, `pull_request`, `workflow_dispatch`;
     `permissions: contents: read`; PR-only concurrency cancellation
2. **`tools/youtube-automation-agent/.github/workflows/ci.yml`** — `master` → `main`
3. **`arabic-educational-skills/remotion/render.mjs`** — select the composition id
   from the plan's format (`Lesson-16x9` / `-9x16` / `-1x1`) instead of the
   non-existent `Lesson`; `--composition` overrides, width/height is the fallback

## 3. Verification actually run

| Check | Command | Result |
| --- | --- | --- |
| Workflow YAML parses and the gate depends on every job | PyYAML load + key/graph assertions | `gate needs == all other jobs: True`, `gate if: ${{ always() }}`, 5 project jobs + `ci` |
| Gate fails on failure/skip/cancel | ran the gate step with synthetic `NEEDS_JSON` | success→`EXIT=0`; failure, skipped, cancelled→`EXIT=1` with `::error` lines |
| `npm ci` for the Remotion engine | `npm ci` in `arabic-educational-skills/remotion` | exit 0, 248 packages |
| Remotion browser command exists | `npx remotion browser ensure --help` | exit 0 |
| Arabic Educational Skills suite | `python -m pytest tests -q` | **108 passed, 3 skipped**, exit 0 (before the fix: 107 passed, 1 failed) |
| Render fix in isolation | `pytest tests/test_plan.py::test_stills_render_all_formats` | **1 passed** (213 s; before: RenderError) |
| Lint | `eslint .` with the projects' own `eslint.config.js`, pinned `eslint@9.39.4` + `@eslint/js@9.39.4` | **exit 0**, no findings |
| `youtube-agent-skill` syntax job | `python -m compileall -q skills` | exit 0 |
| Docs claim vs scripts | `package.json` scripts read directly | job commands map to real scripts (`test`, `lint`, site `test`/`check`/`build`) |

## 4. Checks that could NOT be verified here

Reported as limitations, not passes.

1. **`npm ci` in `tools/youtube-automation-agent` failed locally** with
   `EPERM: unlink ...node_modules\@img\sharp-win32-x64\lib\libvips-cpp-8.17.3.dll`
   (three attempts). A Windows process holds that DLL. Consequence: the
   package's `node_modules` was left partial, so `npm test` could not be re-run
   after the workflow change. No source file in that project was modified.
   Remediation: close the process holding the DLL, then `npm ci`.
2. **`youtube-automation-agent` suite has 2 pre-existing failures (47/49)** from
   the last complete run, both environment-caused, both diagnosed:
   - `Engagement AI Provider Wiring` — the test clears only `OPENAI_API_KEY`, while
     the local gitignored `.env` defines `GEMINI_API_KEY`; the service therefore
     initializes Gemini from the environment and `isAvailable()` is true.
     The product code is correct; CI has no `.env`.
   - `Shorts Repurposing Studio` — `spawn EFTYPE`: `ffmpeg-static` is absent
     (`MODULE_NOT_FOUND`, it is an `optionalDependencies` entry) so the code falls
     back to spawning `ffmpeg`, which fails on this Windows host.
3. **`elephant-goldfish-model` unit tests fail here only on symlink cases** with
   `OSError: [WinError 1314] A required privilege is not held by the client`.
   Windows needs Developer Mode or admin rights to create symlinks; that project's
   own upstream workflow runs Ubuntu + Windows, this repo's job is Ubuntu-only.
4. **No GitHub Actions run was observed** — nothing has been pushed. The workflow
   is validated statically and its logic executed locally; the hosted run is the
   remaining confirmation.

## 5. CI design notes

- There is no `package.json` at the repository root, so no job runs npm there.
- Each JS job caches by that project's own `package-lock.json`.
- `youtube-agent-skill` has no test suite; the job states that and only
  byte-compiles, rather than pretending coverage exists.
- `npx remotion browser ensure` runs because Remotion stills need a browser;
  omitting it would make the suite fail on a clean runner.

## 6. Phase 2–5 status

Not started. Leads noticed while working on Phase 1, unaudited and unverified:

- `tools/youtube-automation-agent/.env` exists locally but is untracked and
  gitignored (`git ls-files | grep '\.env'` shows only `.env.example`). Good.
- During tests the agent logs `API_KEY is not set; mutating API routes are
  unprotected` — an authentication finding for Phase 2.
- The same project ships `oauth-server.js` / `modern-auth.js`; OAuth state
  validation and redirect-URI handling still need the Phase 2 review.
- Arabic error text arrived as mojibake (`��� �������`) through the Windows
  console — encoding, not corruption; relevant to the Phase 3 documentation pass.
- Root `README.md` documents `exports/`, `tiktok/covers/`, `youtube/long-form/`
  while the tree also contains `TIK TOK/`, `YOU TUBE/`, `tools/` — a Phase 3
  accuracy item.
