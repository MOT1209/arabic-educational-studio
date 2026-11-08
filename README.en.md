# 📚 Studio My Channel — YouTube & TikTok

An Arabic educational-video production studio (grammar, morphology, spelling, rhetoric, …) by agenteer.

## 📡 Channels

- **YouTube**: [`@MadrasatiArabic`](https://www.youtube.com/@%D9%85%D8%AF%D8%B1%D8%B3%D8%AA%D9%8A-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9)  (Madrasati Arabic)
- **TikTok**: [`@arbic.skool`](https://www.tiktok.com/@arbic.skool)

---

## 📁 Project Structure

```text
arabic-educational-studio/
├── arabic-educational-skills/     # The core package
│   ├── SKILL.md                   # The playbook: gates and production path
│   ├── engine/                    # Rendering engine: HTML template, fonts, build/assemble
│   ├── scripts/                   # Validation, audio, mux, output checks
│   ├── studio/                    # Studio 3.0 CLI (python -m studio)
│   ├── references/                # Schema, grammar bank, audience and platform profiles
│   ├── schemas/  tests/  remotion/  docs/  examples/
├── youtube/
│   ├── long-form/                 # 16:9 videos (3-12 min)
│   ├── shorts/                    # YouTube Shorts (9:16, ≤60s)
│   ├── metadata/                  # Publication data (SEO, tags, description)
│   └── thumbnails/                # Thumbnails (1280×720)
├── tiktok/
│   ├── shorts/                    # TikTok videos (9:16, ≤60s)
│   ├── metadata/                  # Publication data
│   └── covers/                    # Covers (1080×1920)
├── projects/                      # One folder per video (master-script + video-brief)
├── assets/
│   ├── branding/                  # Logo, intro, outro
│   └── characters/                # Character cards
├── tools/                         # 3 vendored tools (see Project Tools)
├── .github/workflows/ci.yml       # CI, one job per project
└── projects/<video>/exports/      # Render output — per project, generated and git-ignored
```

> There is no `package.json` at the root: every project owns its dependencies and its own `npm` command. Running `npm` from the root is a mistake.

---

## ⚙️ Workflow (according to `arabic-educational-skills/SKILL.md`)

1. **Gate A**: Lesson analysis + idea approval
2. **Gate B**: Writing `master-script.json/md` → `validate_script.py`
3. **Gate C**: Producing a sample scene → approval
4. **Production**: Assets → Animation → Voice → Editing → Export → `check_output.py`

---

## 📦 Requirements

| Requirement | Version | Needed for |
|---|---|---|
| Python | ≥ 3.9 (CI: 3.12) | Package scripts and `studio` |
| ffmpeg + ffprobe | on `PATH` | Rendering, mux, output checks |
| Node.js | ≥ 18.17 | `youtube-automation-agent` and the Remotion engine |

---

## 🚀 Installation

### 1) Clone the repository

```bash
git clone https://github.com/MOT1209/arabic-educational-studio.git
cd arabic-educational-studio
```

### 2) ffmpeg

```bash
# Ubuntu / Debian
sudo apt install ffmpeg
```

```powershell
# Windows
winget install Gyan.FFmpeg
```

### 3) Python dependencies

```bash
python -m pip install -r arabic-educational-skills/requirements-dev.txt
```

`jsonschema` is optional: without it `validate_script.py` falls back to the built-in validator in `studio/core/schema.py`.

### 4) The rendering engine (Remotion)

```bash
cd arabic-educational-skills/remotion
npm ci
npx remotion browser ensure
```

### 5) The YouTube automation agent

```bash
cd tools/youtube-automation-agent
npm ci
npx playwright install chromium    # on Linux add --with-deps
cp .env.example .env               # Windows cmd: copy .env.example .env
```

Fill in at least one provider key in `.env`, then:

```bash
npm run walkthrough    # interactive setup: explains each option, tests keys, connects the channel
npm start              # http://localhost:3456
```

`npm run setup` is the shorter flow; `npm run walkthrough` explains every choice.

---

## 🩺 Environment check

```bash
python arabic-educational-skills/scripts/doctor.py
```

It prints what is available and what is missing, with the command that fixes each gap, and exits with code 1 when something is missing. It never installs anything itself.

---

## 🛠️ Scripts

Run from inside `arabic-educational-skills/`:

| Script | Function |
|---|---|
| `scripts/validate_script.py` | Schema + semantics + diacritics + hash. Options: `--update-hashes`, `--no-engine` |
| `scripts/doctor.py` | Environment check before production |
| `scripts/auto_tashkeel.py` | Suggest diacritics for the text |
| `scripts/validate_brief.py` | Validate `video-brief.json` before writing the script |
| `scripts/voice_pack.py` | Build the line list for recording or generation |
| `scripts/mux_audio.py` | Lay the audio onto the video |
| `scripts/gen_srt.py` | Generate the SRT subtitle file |
| `scripts/retime_from_audio.py` | Re-time lines from the real audio duration |
| `scripts/check_output.py` | Technical check of the final file (ffprobe + SRT) |
| `scripts/aes_common.py` | Shared library (not run directly) |

`validate_script.py`, `check_output.py`, `mux_audio.py`, `retime_from_audio.py` and `auto_tashkeel.py` accept `--help`. `validate_brief.py`, `voice_pack.py` and `gen_srt.py` take a positional path and no flags:

```bash
python scripts/validate_brief.py projects/<project>/video-brief.json
python scripts/voice_pack.py projects/<project>
python scripts/gen_srt.py projects/<project>
```

For the full pipeline:

```bash
python -m studio --help
```

It exposes `new, status, step, submit, approve, reject, modify, regenerate, rewind, compare, resume, verify, interview, styles, providers, lesson, plan, review, assets, subtitles`.

---

## 🔐 Environment variables

The single source of truth is `tools/youtube-automation-agent/.env.example`, where every variable is documented with its default. The essentials:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` or `GEMINI_API_KEY` or `OPENROUTER_API_KEY` … | At least one text provider (details in `docs/providers.md`) |
| `ELEVENLABS_API_KEY` | Higher-quality narration (optional; OpenAI/Gemini are the fallback) |
| `API_KEY` | When set, mutating API routes require the `x-api-key` header |
| `HOST` / `PORT` | Listens on `127.0.0.1:3456` by default; `HOST=0.0.0.0` exposes the dashboard to the network, so set `API_KEY` with it |
| `CHANNEL_NAME` / `DEFAULT_AUTHOR` / `TARGET_AUDIENCE` | Channel identity used during generation |
| `DEFAULT_PRIVACY_STATUS` | Upload privacy, defaults to `private` |
| `FFMPEG_PATH` / `FFPROBE_PATH` | Override the ffmpeg path (order: `FFMPEG_PATH` → `ffmpeg-static` → `PATH`) |
| `YOUTUBE_REDIRECT_URI` | Loopback override for OAuth (requires Desktop app credentials) |

`.env` and `config/credentials.json` are git-ignored; no keys are ever committed.

---

## 🧪 Tests

```bash
cd arabic-educational-skills
python -m pytest tests -q
```

```bash
cd tools/youtube-automation-agent
npm run lint
npm test
```

---

## 🛠️ Project Tools

See `tools/README.md` — 3 vendored repositories:

| Repository | Description |
|---|---|
| `tools/elephant-goldfish-model/` (EGM) | Plugin for Claude Code/Codex/Gemini for software design and review |
| `tools/youtube-agent-skill/` | 11 Claude skills for YouTube management (scripts, hooks, packaging, retention, shorts, viral, seo, chapters, audit) |
| `tools/youtube-automation-agent/` | Self-hosted agent that runs a channel end to end (research → script → voiceover → MP4 → SEO → approval-based publish) |

---

## 🤖 Continuous integration

`.github/workflows/ci.yml` builds each project in its own job on Ubuntu: `arabic-educational-skills` (pytest + Remotion), `youtube-automation-agent` (`npm ci` + lint + test), `youtube-agent-skill` (syntax check), `elephant-goldfish-model` (pytest), `elephant-goldfish-site` (Astro). A final `CI` job fails unless every job succeeded. The audits are in `PHASE1_AUDIT.md` and `PHASE2_SECURITY_AUDIT.md`.

---

## 💡 Notes

- ✅ `grammar-bank.md` needs teacher review before publishing
- 🔤 Arabic text is composed programmatically (HTML/SVG) — do not rely on image generators
- 🏷️ Each scene needs `id` and `hash` (calculated with `validate_script.py --update-hashes`)
- 🛡️ `.gitignore` covers `node_modules/`, `.env`, `config/credentials.json`, `data/`, `uploads/`, `exports/` and media files
- 🗂️ `TIK TOK/` and `YOU TUBE/` are legacy leftovers outside the current pipeline

---

## 📄 Project License

MIT License — see LICENSE for more details.

---

## 🙏 Acknowledgments

Special thanks to community members who contributed to `arabic-educational-skills` and the `youtube-agent-skill` and `youtube-automation-agent` tools.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/MOT1209/arabic-educational-studio/main/youtube/thumbnails/thumbnail-1280x720.jpg" alt="Sample thumbnail" width="400"/>
</p>

<p align="center">
  <sub>Sample Video Thumbnail (1280×720)</sub>
</p>
