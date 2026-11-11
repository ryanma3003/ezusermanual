# Screenshots

Every image in the manual should show what the reader sees, with the part they must use marked by a red box and a numbered marker that matches the step number. Private data must be blurred.

Run Python tools via `<skill>/scripts/run.sh <tool>.py …`.

## Web applications (Playwright)

### 1. Explore

```bash
run.sh capture_web.py inspect --url https://app.example.com/orders --storage-state user-manual/auth.json --screenshot user-manual/shots/_explore-orders.png
```

The output lists each visible control: role, on-screen name, a selector to use in plans, and position. Use these names verbatim in the manual text. Add `--device "iPhone 13"` for a mobile website, and `--wait-for "<selector>"` if the page loads slowly.

### 2. Sign in

- **User signs in by hand:** `run.sh capture_web.py login --url https://app.example.com/login --out user-manual/auth.json`. Tell the user: "A browser window has opened. Please sign in, then close the window." (Optional: `--until-url "/dashboard"` finishes automatically after sign-in.) Then use `"storage_state": "auth.json"` in plans.
- **Credentials from the user:** have the user export them as environment variables (or set them yourself in the shell for that command only), e.g. `MANUAL_USER=… MANUAL_PASSWORD=… run.sh capture_web.py shoot plan.json`. Reference them as `${MANUAL_USER}` in the plan. Never write the real values into files. Add `"save_storage_state": "auth.json"` so later plans can skip sign-in.

To show the sign-in page itself, take that shot in a plan **without** `storage_state`.

### 3. Shot plan (`plan.json`)

Paths are relative to the plan file. Shots run in order **in the same browser tab**, so each shot continues from where the previous one ended. A shot without `url` stays on the current page.

```json
{
  "base_url": "https://app.example.com",
  "viewport": {"width": 1366, "height": 768},
  "device_scale_factor": 2,
  "locale": "en-US",
  "storage_state": "auth.json",
  "outdir": "shots",
  "blur": [".user-email", "[data-testid=avatar-name]"],
  "shots": [
    {
      "name": "02-01-main-screen",
      "url": "/dashboard",
      "wait_for": "text=Welcome",
      "highlight": [
        {"selector": "nav >> role=link[name=/Orders/i]", "label": "1"},
        {"selector": "#search", "label": "2"},
        {"selector": "role=button[name=/Profile/i]", "label": "3"}
      ]
    },
    {
      "name": "03-01-new-order-form",
      "actions": [
        {"click": "role=link[name=/Orders/i]"},
        {"click": "role=button[name=/New order/i]"},
        {"fill": "#customer", "value": "Sample Customer"}
      ],
      "wait_for": "role=dialog",
      "clip": "role=dialog",
      "highlight": [
        {"selector": "#customer", "label": "1"},
        {"selector": "role=button[name=/Save/i]", "label": "2"}
      ],
      "blur": ["#customer-phone"]
    }
  ]
}
```

Plan fields:

| Field | Meaning |
|---|---|
| `base_url` | Joined with each relative `url` / `goto` |
| `viewport`, `device_scale_factor` | Window size in CSS pixels; 2 gives sharp images (default 1366×768 @2) |
| `device` | Instead of viewport: a Playwright device name such as `"iPhone 13"` or `"Pixel 7"` (mobile websites) |
| `locale` | Browser language, e.g. `"id-ID"`, so dates and numbers match the manual language |
| `storage_state` / `save_storage_state` | Load / save the signed-in session |
| `headless` | `false` to watch the browser while it works |
| `blur` | Selectors blurred in **every** shot (all matches) |

Shot fields:

| Field | Meaning |
|---|---|
| `name` | Output file `shots/<name>.png`. Use `CC-NN-description` (chapter-order) for easy sorting |
| `url` | Open this page first (optional) |
| `actions` | Steps before the picture. Each object has exactly one of: `click`, `dblclick`, `fill` (+`value`), `type` (+`value`, typed key by key), `press` (key such as `"Enter"`; optional `on` selector), `select` (+`value` or `label`), `check`, `uncheck`, `hover`, `scroll_to`, `wait_for` (+optional `timeout_ms`), `wait_ms`, `goto`, `upload` (+`file`) |
| `wait_for` | Selector that must be visible before the picture |
| `highlight` | List of `{"selector", "label"}`: red box + numbered marker on the first match. Labels should equal the step numbers |
| `blur` | Extra selectors to blur in this shot |
| `clip` | Crop the picture to this element (plus `clip_margin`, default 48 px, which leaves room for the markers), e.g. a dialog or form |
| `full_page` | Capture the whole scrolling page |
| `skip_screenshot` | Only run the actions (e.g. sign-in) |

Selectors: Playwright syntax. Prefer the ones `inspect` prints: `#id`, `[data-testid=…]`, `role=button[name=/Save/i]` (case-insensitive; also matches names that include icons), `text=Exact words`, and chain with `>>` to narrow down (`nav >> text=Orders`).

When a shot fails, the error names the shot and saves `shots/_failure.png` showing the screen at that moment. Look at it, fix the plan, and run again.

**Avoid changing real data.** Do not click Save, Delete, Send, or Pay on a live system unless the user agreed or the account is a test account. Fill in a form and screenshot it *before* saving.

## Desktop applications (macOS)

```bash
scripts/capture_macos.sh window "App Name" user-manual/shots/04-01-settings.raw.png   # front window of the app
scripts/capture_macos.sh pick  user-manual/shots/x.raw.png                            # user clicks a window
scripts/capture_macos.sh screen user-manual/shots/x.raw.png                           # entire screen
```

The terminal app needs **Screen Recording** permission (and **Accessibility** for `window`). If the capture fails, ask the user to grant it in System Settings › Privacy & Security, then restart the terminal.

Navigating: if your harness can control the computer, use it. Otherwise ask the user, one screen at a time: "Please open **Settings › Printers** in the app and tell me when it is on screen." Then capture.

## Mobile applications

```bash
scripts/capture_mobile.sh devices                                   # what is connected
scripts/capture_mobile.sh android user-manual/shots/05-01-home.raw.png
scripts/capture_mobile.sh ios     user-manual/shots/05-01-home.raw.png
```

- Android (device with USB debugging, or emulator): you can navigate yourself with `adb shell input tap X Y` (pixel coordinates from a screenshot), `adb shell input text "…"`, and `adb shell input keyevent BACK`.
- iOS Simulator: navigation needs the user (or your computer-control tool). Ask them to open each screen.
- Phone screenshots are tall. The builder limits image height automatically. Set `width_cm` around 7–8 if you want them smaller.

## Annotating desktop/mobile screenshots

1. Make a grid copy to read pixel positions: `run.sh annotate.py grid shots/x.raw.png shots/_grid.png` and look at `_grid.png` (lines every 100 px, labeled).
2. Draw: `run.sh annotate.py draw shots/x.raw.png shots/x.png --box 820,40,120,44:1 --box 30,300,260,48:2 --blur 1000,10,240,40`
   - `--box X,Y,W,H:LABEL` (pixels in the raw image; label optional)
   - `--blur X,Y,W,H`
3. Look at the result. Adjust and redraw until the boxes sit exactly on the targets.
4. Delete `*.raw.png` and `_grid.png` when the final images are good.

## Quality checklist

- Readable: no tiny text. Prefer clipping to a dialog or an area over a huge full screen.
- Consistent window size across all shots.
- Realistic but fake sample data. No real names, emails, phone numbers, addresses, account numbers, or balances unless blurred.
- No developer tools, error pop-ups, or "cookie" banners in the frame (close them with an action first).
