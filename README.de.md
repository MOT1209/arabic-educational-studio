# 📚 Studio My Channel — YouTube & TikTok

Ein Studio für arabische Lehrvideos (Grammatik, Morphologie, Rechtschreibung, Rhetorik, …) von agenteer.

## 📡 Kanäle

- **YouTube**: [`@MadrasatiArabic`](https://www.youtube.com/@%D9%85%D8%AF%D8%B1%D8%B3%D8%AA%D9%8A-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9)  (Madrasati Arabic)
- **TikTok**: [`@arbic.skool`](https://www.tiktok.com/@arbic.skool)

---

## 🗂️ Projektstruktur

```text
arabic-educational-studio/
├── arabic-educational-skills/     # Das Kernpaket
│   ├── SKILL.md                   # Das Playbook: Gates und Produktionspfad
│   ├── engine/                    # Render-Engine: HTML-Vorlage, Schriften, build/assemble
│   ├── scripts/                   # Validierung, Audio, Mux, Ausgabeprüfung
│   ├── studio/                    # Studio-3.0-CLI (python -m studio)
│   ├── references/                # Schema, Grammatikbank, Zielgruppen- und Plattformprofile
│   ├── schemas/  tests/  remotion/  docs/  examples/
├── youtube/
│   ├── long-form/                 # 16:9-Videos (3–12 Min.)
│   ├── shorts/                    # YouTube Shorts (9:16, ≤60 s)
│   ├── metadata/                  # Publikationsdaten (SEO, Tags, Beschreibung)
│   └── thumbnails/                # Thumbnails (1280×720)
├── tiktok/
│   ├── shorts/                    # TikTok-Videos (9:16, ≤60 s)
│   ├── metadata/                  # Publikationsdaten
│   └── covers/                    # Covers (1080×1920)
├── projects/                      # Ein Ordner pro Video (master-script + video-brief)
├── assets/
│   ├── branding/                  # Logo, Intro, Outro
│   └── characters/                # Charakterkarten
├── tools/                         # 3 eingebundene Werkzeuge (siehe Projekt-Tools)
├── .github/workflows/ci.yml       # CI, ein Job pro Projekt
└── projects/<Video>/exports/      # Render-Ausgabe — pro Projekt, generiert und in git ignoriert
```

> Im Wurzelverzeichnis gibt es kein `package.json`: Jedes Projekt besitzt seine eigenen Abhängigkeiten und sein eigenes `npm`-Kommando. `npm` im Wurzelverzeichnis auszuführen ist ein Fehler.

---

## ⚙️ Workflow (gemäß `arabic-educational-skills/SKILL.md`)

1. **Gate A**: Lektionsanalyse + Ideenzulassung
2. **Gate B**: Schreiben von `master-script.json/md` → `validate_script.py`
3. **Gate C**: Erstellen einer Musterszene → Genehmigung
4. **Produktion**: Assets → Animation → Stimme → Schnitt → Export → `check_output.py`

---

## 📦 Voraussetzungen

| Voraussetzung | Version | Wofür |
|---|---|---|
| Python | ≥ 3.9 (CI: 3.12) | Paket-Skripte und `studio` |
| ffmpeg + ffprobe | im `PATH` | Rendern, Mux, Ausgabeprüfung |
| Node.js | ≥ 18.17 | `youtube-automation-agent` und die Remotion-Engine |

---

## 🚀 Installation

### 1) Repository klonen

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

### 3) Python-Abhängigkeiten

```bash
python -m pip install pytest jsonschema pyyaml pillow numpy
```

`jsonschema` ist optional: Fehlt es, nutzt `validate_script.py` den eingebauten Validator in `studio/core/schema.py`.

### 4) Die Render-Engine (Remotion)

```bash
cd arabic-educational-skills/remotion
npm ci
npx remotion browser ensure
```

### 5) Der YouTube-Automationsagent

```bash
cd tools/youtube-automation-agent
npm ci
npx playwright install chromium    # unter Linux mit --with-deps
cp .env.example .env               # Windows cmd: copy .env.example .env
```

Tragen Sie mindestens einen Provider-Schlüssel in `.env` ein, dann:

```bash
npm run walkthrough    # interaktive Einrichtung: erklärt jede Option, testet die Schlüssel, verbindet den Kanal
npm start              # http://localhost:3456
```

`npm run setup` ist der kürzere Weg; `npm run walkthrough` erklärt jede Wahl.

---

## 🩺 Umgebungsprüfung

```bash
python arabic-educational-skills/scripts/doctor.py
```

Das Skript zeigt, was vorhanden ist und was fehlt, jeweils mit dem Befehl zur Behebung, und endet mit Code 1, wenn etwas fehlt. Es installiert selbst nichts.

---

## 🛠️ Skripte

Auszuführen aus `arabic-educational-skills/`:

| Skript | Funktion |
|---|---|
| `scripts/validate_script.py` | Schema + Semantik + Diakritika + Hash. Optionen: `--update-hashes`, `--no-engine` |
| `scripts/doctor.py` | Umgebungsprüfung vor der Produktion |
| `scripts/auto_tashkeel.py` | Diakritika für den Text vorschlagen |
| `scripts/validate_brief.py` | `video-brief.json` vor dem Skript prüfen |
| `scripts/voice_pack.py` | Zeilenliste für Aufnahme oder Generierung erstellen |
| `scripts/mux_audio.py` | Audio auf das Video legen |
| `scripts/gen_srt.py` | SRT-Untertiteldatei erzeugen |
| `scripts/retime_from_audio.py` | Zeiten aus der echten Audiolänge neu setzen |
| `scripts/check_output.py` | Technische Prüfung der Enddatei (ffprobe + SRT) |
| `scripts/aes_common.py` | Gemeinsame Bibliothek (nicht direkt ausführen) |

`validate_script.py`, `check_output.py`, `mux_audio.py`, `retime_from_audio.py` und `auto_tashkeel.py` akzeptieren `--help`. `validate_brief.py`, `voice_pack.py` und `gen_srt.py` erwarten einen Positionsparameter und keine Optionen:

```bash
python scripts/validate_brief.py projects/<Projekt>/video-brief.json
python scripts/voice_pack.py projects/<Projekt>
python scripts/gen_srt.py projects/<Projekt>
```

Für die vollständige Pipeline:

```bash
python -m studio --help
```

Verfügbar sind `new, status, step, submit, approve, reject, modify, regenerate, rewind, compare, resume, verify, interview, styles, providers, lesson, plan, review, assets, subtitles`.

---

## 🔐 Umgebungsvariablen

Einzige Quelle der Wahrheit ist `tools/youtube-automation-agent/.env.example`, wo jede Variable mit ihrem Standardwert dokumentiert ist. Die wichtigsten:

| Variable | Zweck |
|---|---|
| `OPENAI_API_KEY` oder `GEMINI_API_KEY` oder `OPENROUTER_API_KEY` … | Mindestens ein Text-Provider (Details in `docs/providers.md`) |
| `ELEVENLABS_API_KEY` | Höherwertige Sprachausgabe (optional; OpenAI/Gemini als Rückfall) |
| `API_KEY` | Wenn gesetzt, verlangen verändernde API-Routen den Header `x-api-key` |
| `HOST` / `PORT` | Hört standardmäßig auf `127.0.0.1:3456`; `HOST=0.0.0.0` macht das Dashboard im Netz sichtbar, dann `API_KEY` setzen |
| `CHANNEL_NAME` / `DEFAULT_AUTHOR` / `TARGET_AUDIENCE` | Kanalidentität für die Generierung |
| `DEFAULT_PRIVACY_STATUS` | Upload-Sichtbarkeit, Standard `private` |
| `FFMPEG_PATH` / `FFPROBE_PATH` | ffmpeg-Pfad überschreiben (Reihenfolge: `FFMPEG_PATH` → `ffmpeg-static` → `PATH`) |
| `YOUTUBE_REDIRECT_URI` | Loopback-Überschreibung für OAuth (erfordert Desktop-App-Zugangsdaten) |

`.env` und `config/credentials.json` sind in git ignoriert; es werden keine Schlüssel eingecheckt.

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

## 🛠️ Projekt-Tools

Siehe `tools/README.md` — 3 eingebundene Repositorys:

| Repository | Beschreibung |
|---|---|
| `tools/elephant-goldfish-model/` (EGM) | Plugin für Claude Code/Codex/Gemini für Software-Design und Code-Review |
| `tools/youtube-agent-skill/` | 11 Claude-Fähigkeiten für YouTube-Management (Skripte, Hooks, Verpackung, Retention, Shorts, Viral, SEO, Kapitel, Audit) |
| `tools/youtube-automation-agent/` | Selbstgehosteter Agent, der einen Kanal vollständig führt (Recherche → Skript → Sprachausgabe → MP4 → SEO → Veröffentlichen nach Genehmigung) |

---

## 🤖 Kontinuierliche Integration

`.github/workflows/ci.yml` baut jedes Projekt in einem eigenen Job auf Ubuntu: `arabic-educational-skills` (pytest + Remotion), `youtube-automation-agent` (`npm ci` + Lint + Test), `youtube-agent-skill` (Syntaxprüfung), `elephant-goldfish-model` (pytest), `elephant-goldfish-site` (Astro). Ein abschließender `CI`-Job schlägt fehl, wenn nicht jeder Job erfolgreich war. Die Audits stehen in `PHASE1_AUDIT.md` und `PHASE2_SECURITY_AUDIT.md`.

---

## 💡 Hinweise

- ✅ `grammar-bank.md` benötigt eine Lehrerprüfung vor der Veröffentlichung
- 🔤 Arabischer Text wird programmatisch gesetzt (HTML/SVG) — verlassen Sie sich nicht auf Bildgeneratoren
- 🏷️ Jede Szene benötigt `id` und `hash` (berechnet mit `validate_script.py --update-hashes`)
- 🛡️ `.gitignore` deckt `node_modules/`, `.env`, `config/credentials.json`, `data/`, `uploads/`, `exports/` und Mediendateien ab
- 🗂️ `TIK TOK/` und `YOU TUBE/` sind Altbestände außerhalb der aktuellen Pipeline

---

## 📄 Projekt-Lizenz

MIT License — siehe LICENSE für weitere Details.

---

## 🙏 Anerkennung

Besonderer Dank an Community-Mitglieder, die zu `arabic-educational-skills` und den Werkzeugen `youtube-agent-skill` und `youtube-automation-agent` beigetragen haben.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/MOT1209/arabic-educational-studio/main/youtube/thumbnails/thumbnail-1280x720.jpg" alt="Beispiel-Thumbnail" width="400"/>
</p>

<p align="center">
  <sub>Beispiel-Video-Thumbnail (1280×720)</sub>
</p>
