# User Manual Skill

An [Agent Skill](https://agentskills.io) that has your AI coding agent write a **non-technical user manual** for an application and export it as **DOCX and/or PDF**.

The manual includes:

- Cover page (logo, app name, version, date, organization, author)
- Revision history
- Table of contents with page numbers
- Numbered chapters and sections (1, 1.1, 1.1.1)
- Screenshots taken from the running app, with red highlight boxes, numbered markers that match the steps, and private data blurred
- Plain, friendly language for readers with no technical background, in English, Bahasa Indonesia, or any other language

Supports web apps (taken automatically with a headless browser), macOS desktop apps, and mobile apps (Android emulator/device, iOS Simulator).

## Install

```bash
git clone <repository-url> usermanual-skill
cd usermanual-skill
./install.sh
```

The installer finds the agents on your machine, links the skill into each one, and installs its dependencies into a private Python environment.

| Agent | Skill folder | `--target` |
|---|---|---|
| Claude Code | `~/.claude/skills` | `claude` |
| Codex, Gemini CLI, Cursor, OpenCode, other Agent Skills tools | `~/.agents/skills` | `agents` |
| oh-my-pi (omp) | `~/.omp/agent/skills` | `omp` |
| Hermes Agent | `~/.hermes/skills` | `hermes` |
| OpenCode (own folder) | `~/.config/opencode/skills` | `opencode` |

Options:

```bash
./install.sh --target claude,agents   # choose targets (or: all)
./install.sh --copy                   # copy instead of symlink
./install.sh --no-deps                # skip dependency setup
./install.sh --uninstall              # remove from all agents + delete the Python environment
```

By default the skill is **symlinked**, so `git pull` updates every agent at once. Restart your agent after installing.

### Requirements

- Python 3.9+
- LibreOffice. It does the page layout, TOC page numbers, and PDF export. The installer tells you how to install it if it is missing:
  - macOS `brew install --cask libreoffice`
  - Ubuntu/Debian `sudo apt-get install -y libreoffice-writer`
  - Windows `winget install TheDocumentFoundation.LibreOffice`
- Installed automatically: python-docx, Pillow, Playwright + Chromium, pypdf, pypdfium2 (in `~/.local/share/user-manual-skill`)
- Optional: `adb` (Android) or Xcode (iOS Simulator) for mobile screenshots

Windows: run the installer from Git Bash or WSL and use `--copy`.

## Use

Ask your agent, for example:

> Create a user manual for https://app.example.com

> Buatkan panduan pengguna untuk aplikasi kasir kami di http://localhost:3000

The agent will:

1. Ask you about the app, language, structure (standard / by user role / by task), readers, cover details, sign-in method, private data to hide, and output format.
2. Explore the app and show you an outline for approval.
3. Take and annotate the screenshots.
4. Write the manual in plain language and build `user-manual/output/<App> - User Manual.docx` / `.pdf`.
5. Check the rendered pages and fix problems before handing the files over.

To sign in, you can either give test credentials (used through environment variables, never written to files) or sign in yourself in a browser window the agent opens.

## Troubleshooting

| Problem | Fix |
|---|---|
| `LibreOffice not found` | Install LibreOffice, or `export SOFFICE=/path/to/soffice` |
| macOS desktop screenshots fail | Give your terminal app **Screen Recording** (and **Accessibility**) permission in System Settings › Privacy & Security, then restart it |
| Chromium fails to start on Linux | `~/.local/share/user-manual-skill/venv/bin/python -m playwright install-deps chromium` |
| Table of contents looks different in Word | Page numbers are computed with LibreOffice's layout. In Word, right-click the table of contents › **Update Field** |

## Layout

```
install.sh                         multi-agent installer
skills/user-manual/
  SKILL.md                         workflow the agent follows
  references/writing-style.md      plain-language rules + word list (EN/ID)
  references/manual-spec.md        manual.json format
  references/screenshots.md        web / desktop / mobile capture and annotation
  scripts/setup.sh, run.sh         dependency setup and tool runner
  scripts/capture_web.py           inspect / login / shoot (Playwright)
  scripts/capture_macos.sh         macOS window capture
  scripts/capture_mobile.sh        Android / iOS Simulator capture
  scripts/annotate.py              boxes, numbered markers, blur, coordinate grid
  scripts/build_manual.py          manual.json → DOCX / PDF
```
