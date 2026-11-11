# `manual.json` format

One JSON file describes the whole manual. Relative file paths (logo, images) are resolved from the folder that contains `manual.json`.

**Do not type numbers into titles.** Chapter/section numbers (1, 1.1, 1.1.1), figure numbers, the table of contents, and page numbers are all generated.

```json
{
  "language": "en",
  "paper": "A4",
  "theme": {"primary_color": "#1F4E79", "font": "Arial"},
  "cover": {
    "app_name": "ShopDesk",
    "title": "User Manual",
    "subtitle": "For store staff",
    "logo": "assets/logo.png",
    "version": "2.3",
    "date": "11 November 2026",
    "company": "PT Contoh Sejahtera",
    "author": "Customer Support Team"
  },
  "revision_history": [
    {"version": "1.0", "date": "1 March 2026", "author": "Rina", "changes": "First release"},
    {"version": "2.3", "date": "11 November 2026", "author": "Support Team", "changes": "Added the Returns chapter"}
  ],
  "sections": [
    {
      "title": "Introduction",
      "blocks": [
        {"type": "paragraph", "text": "ShopDesk helps you record sales and check stock."},
        {"type": "bullets", "items": ["Words in **bold** are the exact words you see on screen.", "Red boxes with numbers in the pictures match the numbered steps."]}
      ]
    },
    {
      "title": "Getting Started",
      "subsections": [
        {
          "title": "Sign in",
          "blocks": [
            {"type": "paragraph", "text": "You need your username and password. Ask your manager if you do not have them."},
            {"type": "steps", "items": [
              "Open your web browser and go to **shop.example.com**.",
              "In the **Email** box, type your email address.",
              {"text": "Click **Sign in**.", "image": "shots/02-01-sign-in.png", "caption": "The sign-in page"}
            ]},
            {"type": "paragraph", "text": "The **Home** page opens."},
            {"type": "note", "kind": "tip", "text": "Tick **Remember me** to stay signed in on your own computer."}
          ]
        }
      ]
    },
    {
      "title": "Glossary",
      "blocks": [
        {"type": "table", "headers": ["Word", "Meaning"], "rows": [["SKU", "The short code printed on each product label."]], "widths_cm": [4, 12]}
      ]
    }
  ]
}
```

## Top level

| Key | Required | Notes |
|---|---|---|
| `language` | no (default `en`) | `en` and `id` have built-in labels. Any other code needs `labels` |
| `labels` | for other languages | Overrides fixed words. Keys: `user_manual`, `toc`, `revision_history`, `version`, `date`, `author`, `changes`, `prepared_by`, `figure`, `page`, `tip`, `note`, `warning` |
| `paper` | no (default `A4`) | `A4` or `Letter` |
| `theme.primary_color` | no (default `#1F4E79`) | Hex color for headings, table headers, the cover |
| `theme.font` | no (default `Arial`) | Use a font installed on both the build machine and readers' machines |
| `cover` | yes | `app_name` is required. Optional: `title` (default "User Manual"/"Panduan Pengguna"), `subtitle`, `logo`, `version`, `date`, `company`, `author`. Omitted fields are left out |
| `revision_history` | no | List of `{version, date, author, changes}`. Omit to skip the page |
| `sections` | yes | Chapters. Each starts on a new page |

## Sections

`{"title": "…", "blocks": [ … ], "subsections": [ … ]}`. At most 3 levels (chapter → section → subsection). Blocks render first, then subsections.

## Blocks

Text in any block can mark on-screen words with `**double asterisks**` (shown in bold). No other formatting syntax is supported.

| Type | Fields | Renders as |
|---|---|---|
| `paragraph` | `text` | Normal paragraph |
| `steps` | `items` (strings, or `{text, image, caption, width_cm}`), optional `start` | Numbered steps 1, 2, 3 …; an item's `image` appears right under that step |
| `bullets` | `items` | Bullet list |
| `image` | `path`, `caption`, optional `width_cm` | Centered picture with a thin border and "Figure C.N: caption" |
| `note` | `kind` (`tip` / `note` / `warning`), `text` | Colored box with the label "Tip:", "Note:", or "Important:" |
| `table` | `headers`, `rows`, optional `widths_cm` | Table with a colored header row (total width ≈ 16 cm on A4) |
| `page_break` | none | Starts a new page |

Images fill the text width (16 cm on A4) unless `width_cm` is set, and are never taller than 17 cm. Give every image a `caption`. Figures are numbered per chapter.

## Build

```bash
run.sh build_manual.py user-manual/manual.json --outdir user-manual/output --formats docx,pdf [--name "ShopDesk User Manual v2.3"]
```

The builder prints the finished table of contents with page numbers, followed by the written files. Errors name the problem (missing image, unknown block type, bad color, …). Fix the cause and run it again.

Page numbers: cover has none; revision history and table of contents use i, ii, iii; Chapter 1 starts at page 1. In Word, the table of contents is a real TOC field that stays clickable and can be refreshed (right-click › Update Field).
