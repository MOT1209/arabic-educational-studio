# Phase 5 — Final hardening, contract enforcement, cleanup

Scope: everything left open after Phase 4 — the Phase 2 auth findings, the
Phase 4 decisions D2/D5/D6/D7/D8/D9, and the uncommitted ffmpeg/test work.
Every change below was made against the code that existed; no file was
rewritten wholesale.

## 1. Security (Phase 2 items)

| Item | Change | Where |
| --- | --- | --- |
| C2 fail-open | A non-loopback `HOST` with no `API_KEY` now refuses to start (`process.exit(1)`) instead of printing a warning. Loopback without a key stays open, as designed. | `index.js::start`, `bindSafetyError` |
| C3 comparison | Header comparison is constant-time over SHA-256 digests, so a wrong-length guess cannot throw and timing does not leak byte by byte. | `index.js::apiKeyMatches` |
| C3 storage | The dashboard keeps the key in `sessionStorage` instead of `localStorage`, so it dies with the tab. | `dashboard/app.js` |
| C4 reads | When `API_KEY` is set, every `/api` route requires it. Generated thumbnails/stills remain readable because `<img src>` cannot send a header. | `index.js` mount |
| A3 PKCE | All three authorization flows send an S256 `code_challenge` and exchange the code with the verifier. Verifiers are per-request and cleared after use. | `utils/pkce.js`, `modern-auth.js`, `oauth-server.js`, `utils/credential-manager.js` |
| A4 scopes | Dropped the redundant broad `.../auth/youtube` scope from all three flows. The remaining set is upload + readonly + analytics + force-ssl (comment posting). | three scope arrays |

`force-ssl` is still requested because comment posting is a shipped feature; it
is gated at runtime by `postingEnabled` and the reply-approval flow.

## 2. Contracts and dependencies

- **D2**: `arabic-educational-skills/requirements-dev.txt` now declares the test
  dependencies (`pytest`, `jsonschema`, `pillow`, `numpy`). CI installs from the
  file, and all three READMEs do the same. The unused `pyyaml` is gone.
- **D5**: `render_props()` emits `props_version: "1.0"`; `render.mjs` exits 2 on
  a missing or unknown major (the guard lives in `remotion/props-version.mjs` so
  it is testable without Remotion installed). `test_plan.py` asserts the version
  is present and that the guard rejects props without it.
- **D8**: new `skill-mirror` CI job diffs every `.claude/skills/<name>` against
  `tools/*/skills/<name>` (excluding untracked `__pycache__`) and fails if the
  directory count differs.
- **D9**: `tools/youtube-agent-skill/tests/test_tools.py` runs all six tools:
  no-argument usage must print text and must not traceback; `hookscore --hook`
  and `title --title/--thumb` must succeed. CI runs `unittest discover`.

## 3. Cleanup

- Untracked the four committed videos (`youtube/long-form/*.mp4` ×3 and
  `projects/project-01-inna/exports/scene_01.mp4`) with `git rm --cached`; the
  files remain on disk and are now covered by the existing ignore rules.
- Removed the empty legacy directories `TIK TOK/` and `YOU TUBE/` (no tracked
  files were in them).
- Committed the pending `utils/ffmpeg.js` fix (verify the bundled binary runs
  before using it, fall back to `PATH`) and the two `GEMINI_API_KEY` test
  isolation fixes, with the file's missing trailing newline restored.

## 4. Verification actually run

```
$ node --check index.js test.js modern-auth.js oauth-server.js \
    utils/credential-manager.js utils/pkce.js utils/ffmpeg.js \
    dashboard/app.js eslint.config.js
  → all ok
$ python -m py_compile plan.py tests/test_plan.py tests/test_tools.py
  → ok
$ python -m unittest discover -s tools/youtube-agent-skill/tests -v
  → Ran 3 tests ... OK (8.0s)
$ python -m pytest tests/test_plan.py::test_render_props_and_listening_caption_hidden -q
  → 1 passed in 2.75s
$ python -c "import yaml; ... ci.yml"
  → jobs: [arabic-educational-skills, youtube-automation-agent, youtube-agent-skill,
           elephant-goldfish-model, elephant-goldfish-site, skill-mirror, ci]
  → needs includes skill-mirror
```

Not run locally:

- `npm test` for YTA: the local `node_modules` is incomplete (a previous
  `npm ci` failed with `EPERM` on sharp's DLL); `node -e "require('./index')"`
  stops on a missing third-party module, and ESLint is not installed. CI runs
  `npm ci`, lint, and the full suite on a clean runner.
- The full AES suite exceeds five minutes locally; CI runs the exact documented
  command.
- PKCE and the fail-closed bind are not live-tested (they need a real Google
  consent round trip); the S256 pair itself is unit-tested.

Hosted CI for this phase:

- Run [42473223557](https://github.com/MOT1209/arabic-educational-studio/actions/runs/42473223557)
  (`f5a52d4`): six jobs green; `YouTube Automation Agent` failed because the
  pre-existing bind test still asserted the unkeyed `HOST=0.0.0.0` override
  that this phase removed.
- Run [42474731314](https://github.com/MOT1209/arabic-educational-studio/actions/runs/42474731314)
  (`1481f4c`): all seven jobs green after that test was rewritten to require
  `API_KEY` for the override and to restore the previous key value.

## 5. Remaining risks and limits

1. **Re-authorization**: narrowing the scopes does not revoke anything. Existing
   `tokens.json` keeps the old grant until the owner re-runs
   `npm run walkthrough`; until then the consent screen still shows the old set.
2. **Asset reads**: `/api/content/:id/asset/:kind` (and the scene/shorts
   variants) remain unauthenticated by design because `<img>` cannot send a
   header. They serve generated media, not credentials.
3. **Public surface**: `GET /health` is intentionally public; the legacy
   `/analytics` and `/schedule` pages are not under `/api` and are unchanged.
4. **PKCE exchange**: `getToken({ code, codeVerifier })` is the documented
   google-auth-library form, but only a live authorization proves the full
   round trip.
5. **YTA dependency health**: the local install is broken (sharp `EPERM`); CI's
   clean `npm ci` is the only proof the dependency set installs.
6. **Publishing handoff (C7)** is still manual and unversioned. No feature was
   invented for it in this phase.
