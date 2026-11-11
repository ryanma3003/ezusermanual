---
name: user-manual
description: Create a non-technical, step-by-step user manual for a web, desktop (macOS) or mobile application and export it to DOCX and/or PDF with a cover page, revision history, table of contents with page numbers, numbered sections/subsections, and annotated screenshots (highlight boxes, numbered markers, blurred private data). Use when the user asks for a user manual, user guide, panduan pengguna, buku manual, help document, or end-user documentation for an app.
license: MIT
compatibility: Requires Python 3.9+ and LibreOffice. Screenshots need Playwright (web), macOS screencapture (desktop), adb or Xcode simctl (mobile). Run scripts/setup.sh once.
---

# User Manual

Produce a polished user manual that someone with **no technical background** can follow. Output is a DOCX and/or PDF with:

- Cover page (logo, app name, "User Manual", version, date, company, prepared by)
- Revision history page
- Table of contents with page numbers
- Numbered sections and subsections (1, 1.1, 1.1.1), each chapter on a new page
- Annotated screenshots with figure numbers ("Figure 3.2: …")
- Page numbers in the footer (front matter i, ii, iii; body restarts at 1)

All paths below are relative to this skill's directory (`<skill>`). Run every Python tool through `<skill>/scripts/run.sh <tool>.py …`. It uses the skill's own virtual environment and installs it on first use.

## Workflow

Follow these steps in order. Do not skip step 1, and do not skip the outline approval in step 4.

### 1. Interview the user

Ask everything in **one** message (use a form or question tool if your harness has one). Skip anything the user already answered. Offer sensible defaults.

1. **Which application?** Web address, desktop app name, or mobile app (Android emulator/device or iOS Simulator). Is it running and reachable now?
2. **Language** of the manual (for example English or Bahasa Indonesia). Built-in labels exist for `en` and `id`. Other languages need a `labels` block (see `references/manual-spec.md`).
3. **Structure.** Offer exactly these three:
   - *Standard*: Introduction → Getting Started (opening the app, signing in, finding your way around) → one chapter per menu/feature → Troubleshooting & FAQ → Glossary
   - *By user role*: one chapter per role (Admin, Staff, …), each with its tasks
   - *By task*: chapters named after goals ("How to create an invoice", …)
4. **Readers.** Who will read it (e.g. cashiers, customers, back-office staff), and which roles or features to include or leave out.
5. **Cover details.** App name, logo file path, app/document version, date, company/organization, prepared by (author).
6. **Revision history.** Entries to list. Default: one row with version, today's date, author, "First release".
7. **Sign-in.** Either (a) test credentials you may use (passed as environment variables, never written into files), or (b) the user signs in by hand in a browser window you open. Mention that accounts with demo data give the best screenshots.
8. **Private data to hide** in screenshots (names, emails, phone numbers, balances, …).
9. **Output.** DOCX, PDF, or both (default: both). Paper is A4 by default; Letter on request. Brand color (hex) is optional (default `#1F4E79`).

### 2. Set up (once per machine)

```bash
<skill>/scripts/setup.sh
```

This installs python-docx, Pillow, Playwright and Chromium into a private environment and checks for LibreOffice. If LibreOffice is missing, the script prints the install command. Ask the user before running it.

Create a working folder in the user's current project, e.g. `./user-manual/`, containing `manual.json`, `shots/`, and screenshot plans. Use **absolute paths** or paths relative to `manual.json`.

### 3. Explore the application

Learn the screens, menus, and exact on-screen wording before writing anything.

- **Web:** `run.sh capture_web.py inspect --url <url> [--storage-state auth.json] --screenshot shots/_explore-home.png` prints the page title, headings, and every visible button, link, and field with a ready-to-use selector. Look at the screenshot. Repeat for each menu item.
- **Sign-in (web):**
  - Manual: `run.sh capture_web.py login --url <login-url> --out user-manual/auth.json`. A real browser window opens. Ask the user to sign in and then **close the window**. The session is saved to `auth.json`.
  - Credentials: put a `fill`/`click` sign-in sequence in the first shot of the plan, using `${ENV_VAR}` placeholders, and add `"save_storage_state": "auth.json"` (see `references/screenshots.md`).
- **Desktop (macOS) / mobile:** see `references/screenshots.md`. You capture the screen; when you cannot click inside the app yourself, ask the user to open each screen and tell you when it is ready.

`auth.json` holds a live session. Never print it, and delete it when you finish.

### 4. Propose the outline and get approval

Show the numbered outline (chapters and subsections) in the structure the user chose, plus the list of screenshots you plan to take. Wait for approval or changes.

### 5. Capture screenshots

- **Web:** write a shot plan (`references/screenshots.md`) and run `run.sh capture_web.py shoot plan.json`. The plan clicks through the app, draws red boxes with numbered markers on the elements you name, and blurs private data.
- **Desktop/mobile:** capture with `scripts/capture_macos.sh` / `scripts/capture_mobile.sh`. Then annotate with `run.sh annotate.py` (use `annotate.py grid` to read pixel coordinates).
- Look at every final image. Check that the highlights sit on the right element and that no private data is visible. Retake as needed.
- Marker numbers in a screenshot must match the step numbers in the text that describes it.

### 6. Write `manual.json`

Read `references/writing-style.md` **before writing** and follow it strictly. Read `references/manual-spec.md` for the exact JSON format. Do not number headings yourself. Numbering, figure numbers, the TOC, and page numbers are all automatic.

### 7. Build

```bash
<skill>/scripts/run.sh build_manual.py user-manual/manual.json --outdir user-manual/output --formats docx,pdf --preview user-manual/preview
```

The builder writes the DOCX and lays it out with LibreOffice (headless). It reads the page of every heading and writes those numbers into the table of contents, then exports the PDF. It prints the finished table of contents. Check that every chapter and subsection is listed with a page number. `--preview` renders every page to `preview/page-NN.png`.

### 8. Review before delivering

- Look at the preview pages: cover, revision history, table of contents, every figure (readable? markers visible?), and page breaks (no step separated from its picture, no near-empty pages).
- Re-read the text as a first-time user: is any word technical? Is any step missing? Does every step say where to click?
- Fix the problems and rebuild. Report the output file paths to the user and list anything you could not capture.
- Delete `auth.json`, the `preview/` folder, and the `_explore-*` screenshots.

## Files

| File | Purpose |
|---|---|
| `references/writing-style.md` | Plain-language rules and word replacements (EN + ID). **Required reading.** |
| `references/manual-spec.md` | `manual.json` format: cover, revision history, sections, blocks |
| `references/screenshots.md` | Web shot plans, sign-in, desktop and mobile capture, annotation |
| `scripts/setup.sh` | One-time dependency install |
| `scripts/run.sh` | Runs a skill Python tool inside the skill's environment |
| `scripts/capture_web.py` | `inspect`, `login`, `shoot` for web apps (Playwright) |
| `scripts/capture_macos.sh` | Screenshot of a macOS app window |
| `scripts/capture_mobile.sh` | Screenshot from an Android device/emulator or the iOS Simulator |
| `scripts/annotate.py` | Boxes, numbered markers, blur, coordinate grid |
| `scripts/build_manual.py` | `manual.json` → DOCX/PDF |
