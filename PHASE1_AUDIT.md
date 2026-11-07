# Phase 1 — CI/CD Stabilization Report

Scope: Phase 1 only. Phases 2–5 have not been started, because the master prompt
requires Phase 1 acceptance before proceeding.

Every result below was executed: locally in this working tree, or on the hosted
CI runs linked in section 4. Nothing is inferred.

---

## 1. What was wrong

| Finding | Evidence |
| --- | --- |
| Repository had **no** CI at all | `git ls-files \| grep '^\.github'` returned nothing |
| Vendored workflow targeted a branch that does not exist | `tools/youtube-automation-agent/.github/workflows/ci.yml` triggered on `master`; the repo has only `main` |
| No per-project test entry points existed | 4 independent `package.json` projects plus 3 Python trees, none covered by a workflow |
| A real renderer bug was hidden by the untested suite | `test_stills_render_all_formats` failed with `Could not find composition with ID Lesson. Available compositions: Lesson-16x9, Lesson-9x16, Lesson-1x1` |
| Lock file could not be installed by the npm version CI uses | first hosted run: `npm ci` → `Missing: @types/node@26.6.6 from lock file` |

Nested `.github/` directories under `tools/` are inert on GitHub — only the
repository-root `.github/workflows/` runs. The vendored `master` trigger was
therefore dead configuration, which is why none of the above was visible.

## 2. Changes (4 files, all small)

1. **`.github/workflows/ci.yml`** (new) — one job per independent project plus a
   required-result gate:
   - `arabic-educational-skills` — Ubuntu, Python 3.12, ffmpeg, Remotion `npm ci`,
     `npx remotion browser ensure`, `pytest tests`
   - `youtube-automation-agent` — Node 20 (matches its `engines`), `npm ci`,
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
4. **`tools/youtube-automation-agent/package-lock.json`** — resynced with
   npm 10.8.2, the version CI runs (see section 4)

## 3. Verification run locally

| Check | Command | Result |
| --- | --- | --- |
| Workflow YAML parses; gate depends on every job | PyYAML load + graph assertions | `gate needs == all other jobs: True`, `gate if: ${{ always() }}` |
| Gate fails on failure/skip/cancel | gate step run with synthetic `NEEDS_JSON` | success→`0`; failure, skipped, cancelled→`1` with `::error` lines |
| `npm ci` for the Remotion engine | `npm ci` in `arabic-educational-skills/remotion` | exit 0, 248 packages |
| Remotion browser command exists | `npx remotion browser ensure --help` | exit 0 |
| Arabic Educational Skills suite | `python -m pytest tests -q` | **108 passed, 3 skipped**, exit 0 (before the fix: 107 passed, 1 failed) |
| Render fix in isolation | `pytest tests/test_plan.py::test_stills_render_all_formats` | **1 passed** (213 s; before: RenderError) |
| Lint, each project's own `eslint.config.js` | `eslint .`, pinned `eslint@9.39.4` + `@eslint/js@9.39.4` | exit 0, no findings |
| `youtube-agent-skill` syntax job | `python -m compileall -q skills` | exit 0 |
| Lock file installable by npm 10 | `npx npm@10.8.2 ci --dry-run` | exit 0 |
| Lock file installable by npm 11 | `npm ci --dry-run` | exit 0 |

## 4. Hosted runs — the arbiter

| Run | Result |
| --- | --- |
| [42420253049](https://github.com/MOT1209/arabic-educational-studio/actions/runs/42420253049) | 4 of 5 jobs passed; `youtube-automation-agent` failed at install; the `ci` gate failed the run and emitted `::error` naming it |
| [42421046689](https://github.com/MOT1209/arabic-educational-studio/actions/runs/42421046689) | **all 5 jobs + the gate: success** |

That first hosted run did the job it was built for: it caught a defect no local
check could. `npm ci` refused the lock with `Missing: @types/node@26.6.6 from lock
file`. The lock omitted a nested `node_modules/inquirer/node_modules/@types/node`
entry; npm 11 (this machine) tolerated the gap, npm 10 (CI) refused it. Reproduced
locally with `npx npm@10.8.2 ci --dry-run`, regenerated the lock with that same
npm version, then verified `ci --dry-run` exits 0 under **both** npm 10 and npm 11.
The diff was 11 insertions / 48 deletions, all generated: the missing entry plus
`libc` metadata npm 11 writes and npm 10 does not.

Test counts from the green run:

| Suite | Hosted result |
| --- | --- |
| YouTube Automation Agent | `✅ Passed: 49 / ❌ Failed: 0` |
| Elephant Goldfish Model | `340 passed, 2 skipped in 3.23s` |
| Arabic Educational Skills | `105 passed, 4 skipped in 44.22s` |

This settles both open questions from the local session: the two
`youtube-automation-agent` failures were environmental. The suite is green on a
runner with no `.env`, and `ffmpeg-static` installs on Linux, so `spawn EFTYPE`
cannot occur.

AES reports 105/4 on the runner against 108/3 locally; the extra skips are the
tests gated on local renderer/engine availability.

## 5. Local-environment-only, not repository defects

- `EPERM: unlink ...libvips-cpp-8.17.3.dll` — a Windows process holds the DLL, so
  `npm ci` cannot replace it on this machine. Nothing to change in the repo, and
  the Linux runner installs it fine.
- `OSError: [WinError 1314] A required privilege is not held by the client` in the
  EGM symlink tests — Windows needs Developer Mode or admin rights to create
  symlinks. Those tests pass on the runner.
- `EBADENGINE` warning for `@typespec/ts-http-runtime@0.3.9` (requires Node >= 22)
  while the job runs Node 20. Install and all 49 tests pass, so it is a warning
  only; it is a dependency-graph question for Phase 4.

## 6. CI design notes

- There is no `package.json` at the repository root, so no job runs npm there.
- Each JS job caches by that project's own `package-lock.json`.
- `youtube-agent-skill` has no test suite; the job says so and byte-compiles,
  rather than pretending coverage exists. A `--help` smoke step was tried and
  removed: 5 of its 6 scripts exit 1 on `--help`.
- `npx remotion browser ensure` runs because Remotion stills need a browser;
  without it the suite would fail on a clean runner.
- Keep lock files generated with the npm major that CI uses. A lock that only
  satisfies a newer npm installs nowhere else.

## 7. Phase 2–5 status

Not started. Leads noticed while working on Phase 1, unaudited and unverified:

- `tools/youtube-automation-agent/.env` exists locally but is untracked and
  gitignored (`git ls-files | grep '\.env'` shows only `.env.example`). Good.
- During tests the agent logs `API_KEY is not set; mutating API routes are
  unprotected` — an authentication finding for Phase 2.
- The same project ships `oauth-server.js` / `modern-auth.js`; OAuth state
  validation and redirect-URI handling still need the Phase 2 review.
- Arabic error text arrived as mojibake through the Windows console — encoding,
  not corruption; relevant to the Phase 3 documentation pass.
- Root `README.md` documents `exports/`, `tiktok/covers/`, `youtube/long-form/`
  while the tree also contains `TIK TOK/`, `YOU TUBE/`, `tools/` — a Phase 3
  accuracy item.
