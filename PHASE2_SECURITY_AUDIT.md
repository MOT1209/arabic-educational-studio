# Phase 2 — Security Audit (youtube-automation-agent)

Scope: the four areas requested — OAuth state/redirect handling, token storage,
dashboard API authorization, and credentials in logs.

Method: read every auth-related file, enumerate the full HTTP surface, and
verify each claim by execution where possible. Findings are separated into
**fixed here**, **open**, and **verified good**. Nothing below is inferred from
a file name.

Files read in full: `oauth-server.js`, `modern-auth.js`,
`utils/credential-manager.js`, `utils/logger.js`, `.gitignore`, plus the route
table and bind logic in `index.js` (1885 lines) and `test.js`.

---

## 1. OAuth state and redirect URI

### A1 — No `state` parameter on either callback flow (High, FIXED)

Both flows built an authorization URL and then exchanged any code that arrived
on their loopback port, with nothing tying the callback to the request that
started it.

Evidence before the fix — no occurrence of `state` in any auth file:

```
$ grep -rn "state" modern-auth.js oauth-server.js utils/credential-manager.js
(no output)
```

Why it matters: the callback port is reachable by any process on the machine
(and, in `oauth-server.js`, by any process that can reach `localhost:8080`). A
foreign authorization code accepted there binds the agent to an account the
caller controls — classic login CSRF. The 5-minute window and the predictable
port range make the `modern-auth.js` variant especially reachable.

Fix: each authorization request now generates 32 random bytes
(`crypto.randomBytes(32).toString('hex')`), sends it as `state`, and the
callback compares it with `crypto.timingSafeEqual` before touching the code.
The state is cleared after one use, and a mismatch is refused with HTTP 400
before `getToken` is called. Applied to both `modern-auth.js` and
`oauth-server.js`.

### A2 — Redirect URI handling (verified good)

`modern-auth.js#resolveRedirect` refuses anything that is not `http:` on
`localhost` / `127.0.0.1` / `::1`, skips the obsolete `localhost:8080` redirect
that older installs stored, and picks a random port in 8000–8999 when none is
configured. `YOUTUBE_REDIRECT_URI` can override the list but cannot escape the
loopback check. `oauth-server.js` listens on `127.0.0.1:8080` only. No
open-redirect or attacker-chosen-host path exists.

The browser opener was also verified: `spawn(..., { shell: false })` with an
`https?://` check, so no shell interpolation of the URL.

### A3 — No PKCE (Medium, open)

Neither flow sends `code_challenge` / `code_verifier`. Google's guidance for
installed apps is PKCE even when a client secret ships with the app, because
the secret is not confidential on a user's disk. Recommendation, not applied:
it changes the token-exchange path and deserves its own review.

### A4 — Broad scopes (Low, open)

Both flows request `youtube`, `youtube.upload`, `youtube.readonly`,
`yt-analytics.readonly`, and `youtube.force-ssl` unconditionally, and store an
offline refresh token. `youtube.force-ssl` in particular grants comment and
playlist mutation the pipeline does not obviously need. Recommendation: request
scopes per feature at first use.

### A5 — "Raw error object may leak the client secret" (DISPROVED)

`oauth-server.js` does `console.error(chalk.red('Token exchange failed:'), error)`.
Printing a whole object is a leak risk in principle, so it was tested rather
than assumed. With `googleapis` installed in an isolated directory and a dummy
marker in the secret slot:

```
marker_in_util_inspect: false
marker_in_config_data: false
own_keys: stack,message,cause,config,response,code,status,error
message_head: invalid_client
```

The secret does not appear in the inspected error. Still recommended to log
`error.message` only, since the shape of a vendor error is not a contract.

## 2. Token storage

### B1 — `config/credentials.json` was world-readable (Medium, FIXED)

Token files were already written owner-only (`mode: 0o600` + `chmodSync`) by
both auth flows, and `credential-manager.js` uses a `writePrivateFile` helper.
But nothing tightened a file that already existed, and only
`config/tokens.json` was ever chmod'ed. The credentials file — which holds the
OAuth **client secret** — was on disk as 0644, readable by every local user:

```
$ stat -c '%a %n' config/*.json
644 config/credentials.example.json
644 config/credentials.json
$ grep -rn chmod --include=*.js .
./modern-auth.js:146:  fs.chmodSync(this.tokensPath, 0o600);
./oauth-server.js:90:  fs.chmodSync(tokensPath, 0o600);
./utils/credential-manager.js:13:  await fs.chmod(filePath, 0o600)
```

Fix: `loadCredentials()` and `loadTokens()` now chmod the existing file to 0600
on load, so a file created by an older version stops being readable the first
time the app runs.

### B2 — Secrets are not in the repository (verified good)

```
$ git ls-files | grep -iE "tokens|credential|\.env|\.key|\.pem"
.env.example
config/credentials.example.json
utils/credential-manager.js
```

Only the example files are tracked; `.gitignore` covers `.env`, `config/*.json`,
`*.key`, `*.pem`, `logs/`, `data/*.db`, and the generated media directories.

### B3 — Tokens are stored unencrypted (informational)

At 0600 on a single-user machine this is the normal trade-off for a local
desktop tool. Noting it because the token grants upload rights to the channel;
an encrypted store keyed by an OS credential would be the next step, not a
defect.

## 3. Dashboard API authorization

### C1 — Every mutating route is protected (verified good)

`index.js` has a single `requireAPIKey()` middleware, re-aliased as `protect` in
`setupOperatorAPI`. All write routes carry it, including the multi-line route
whose middleware list is easy to miss:

```
index.js:738   this.app.put('/api/content/:productionId/scenes/:sceneId/asset',
index.js:739     protect,
index.js:740     express.raw({ type: ['image/*','video/*'], limit: '100mb' }),
```

Enumerated 76 `app.*` calls; the only unauthenticated ones are `GET`s and the
static dashboard. Auth is a custom `x-api-key` header, which a cross-site form
cannot set — so there is no CSRF path even though no cookies are used.

### C2 — Fail-open when `API_KEY` is unset (Medium, open — needs your call)

```js
if (!process.env.API_KEY) return next();   // index.js:221
```

The default bind is `127.0.0.1` (loopback), and a regression test asserts it
(`test.js:2165`). But `HOST=0.0.0.0` is honoured, and in that case the code only
prints a warning:

```
⚠️  HOST=0.0.0.0 exposes the dashboard to your network without API_KEY.
```

With `HOST=0.0.0.0` and no `API_KEY`, generation, approval, publishing, and the
asset upload route are all reachable from the LAN. Not changed here: making the
bind fail closed breaks the existing test that asserts `HOST` overrides the
address, so that is a behaviour decision rather than a silent fix. Recommended
change: refuse to start on a non-loopback host unless `API_KEY` is set, and
update that test to assert the refusal.

### C3 — Weaknesses in the auth mechanism itself (Low)

- The key is compared with `!==` rather than a constant-time compare. Practical
  risk over a local socket is negligible, but the fix is one line.
- The dashboard keeps the key in `localStorage`, where any XSS in that origin
  can read it. No XSS sink was found: `escapeHTML()` covers rendered values and
  the auth pages use `esc()` (added in an earlier commit), so this is a blast
  radius note, not a live hole.

### C4 — Read-only endpoints are unauthenticated (Low)

`GET /api/dashboard`, `/api/content/:productionId`, `/api/jobs/:jobId`,
`/api/outcomes`, `/analytics`, `/schedule`, and the asset endpoints serve
channel data without a key. Acceptable on loopback by design; it becomes a data
exposure the moment `HOST` is not loopback (see C2).

## 4. Credentials in logs

### D1 — No secrets in the existing logs (verified good)

The local `logs/` directory holds real output (118 KB in `combined.log` alone).
Searched it, `data/`, and `temp/` for key material:

| Pattern | Matches |
| --- | --- |
| `AIza…` (Google API key) | 0 |
| `sk-…` (OpenAI-style key) | 0 |
| `client_secret` | 0 |
| `refresh_token` | 0 |
| `ya29.…` (Google access token) | 0 |

### D2 — Redaction exists where upstream errors surface (verified good)

`utils/video-providers.js:21` and `utils/production-readiness-service.js:276`
both rewrite `Bearer <token>` to `Bearer [redacted]` before an upstream response
body reaches a log. `utils/logger.js` records `error.message` and `error.stack`
only — never the request object — so a logged response cannot carry an
`Authorization` header.

### D3 — No hardcoded secrets in the dashboard bundle (verified good)

`grep -rnoE "AIza…|sk-…|client_secret" dashboard/` returns nothing; the key is
entered at runtime and kept in the browser.

## 5. Verification

| Check | Command | Result |
| --- | --- | --- |
| Syntax of every edited file | `node --check` on `modern-auth.js`, `oauth-server.js`, `utils/credential-manager.js`, `test.js` | 4/4 OK |
| New regression test, hosted | CI job `youtube-automation-agent` | `✅ OAuth Callback Integrity - PASSED` |
| Full suite, hosted | CI run [42464964470](https://github.com/MOT1209/arabic-educational-studio/actions/runs/42464964470) | `✅ Passed: 50 / ❌ Failed: 0` |
| Lint, hosted | same run | `0 errors` |
| All jobs + gate | same run | **success** |

The new test asserts four things: the state comparator accepts only the exact
issued value (`null` and `''` rejected); a callback carrying a foreign state
gets HTTP 400 on the modern flow; the authorization code is **not** exchanged in
that case; and the legacy Express callback refuses a callback when no flow is
pending. The credentials-mode assertion is POSIX-only, matching the existing
token-mode test, so it ran on the Ubuntu runner but not on Windows.

## 6. Limitations of this audit

- Local `npm ci` for this project is still blocked by `EPERM` on
  `libvips-cpp-8.17.3.dll` (a Windows process holds it), so the suite could not
  be executed locally. The hosted run above is the evidence.
- The audit covered the four requested areas. Command injection, path
  traversal, and stored XSS outside the auth pages were not exhaustively
  traced; the two injection patterns that were checked (browser opener, HTML
  escaping) are reported above.
- CI output shows `DEP0169: url.parse() … prone to errors that have security
  implications` from a dependency, not from repository code. Worth resolving
  with the dependency work in Phase 4.

## 7. Summary

| ID | Area | Severity | Status |
| --- | --- | --- | --- |
| A1 | OAuth state missing on both flows | High | **Fixed** |
| B1 | `credentials.json` world-readable | Medium | **Fixed** |
| C2 | Fail-open when `API_KEY` unset + non-loopback host | Medium | Open — needs a decision |
| A3 | No PKCE | Medium | Open — recommended |
| A4 | Over-broad OAuth scopes | Low | Open — recommended |
| C3 | Non-constant-time key compare, key in `localStorage` | Low | Open |
| C4 | Read-only endpoints unauthenticated | Low | Open — by design on loopback |
| A2, B2, C1, D1–D3 | Redirect handling, secret tracking, route protection, log hygiene | — | Verified good |
