#!/usr/bin/env python3
"""Explore and screenshot web applications for the user manual (Playwright + Chromium).

  capture_web.py inspect --url URL [--storage-state auth.json] [--screenshot out.png] [--device "iPhone 13"]
      Print the page title, headings and every visible button/link/field with a selector to use in plans.

  capture_web.py login --url URL --out auth.json [--until-url REGEX] [--timeout 600]
      Open a visible browser so a person can sign in by hand. The session is saved to --out
      every second; it is finished when the window is closed (or the address matches --until-url).

  capture_web.py shoot plan.json
      Run a screenshot plan (see references/screenshots.md): navigate, act, highlight, blur, save.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotate import blur, highlight  # noqa: E402

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
ACTION_KEYS = ("click", "dblclick", "fill", "type", "press", "select", "check", "uncheck", "hover",
               "scroll_to", "wait_for", "wait_ms", "goto", "upload")


class PlanError(Exception):
    pass


def expand_env(value):
    if isinstance(value, str):
        def sub(m):
            name = m.group(1)
            if name not in os.environ:
                raise PlanError(f"environment variable {name} is not set (used as ${{{name}}} in the plan)")
            return os.environ[name]
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", sub, value)
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    return value


def new_context(pw, browser, *, viewport=None, scale=2, storage_state=None, device=None, locale=None):
    if device and device not in pw.devices:
        raise PlanError(f"unknown device {device!r}; see https://playwright.dev/docs/emulation#devices")
    opts = dict(pw.devices[device]) if device else {"viewport": viewport or DEFAULT_VIEWPORT, "device_scale_factor": scale}
    if storage_state:
        if not Path(storage_state).is_file():
            raise PlanError(f"storage state {storage_state} not found; run 'capture_web.py login' first")
        opts["storage_state"] = str(storage_state)
    if locale:
        opts["locale"] = locale
    return browser.new_context(**opts)


def settle(page, wait_for=None, timeout=15000):
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except PlaywrightTimeout:
        pass  # apps with live connections never go idle; the explicit wait_for below is what matters
    if wait_for:
        page.locator(wait_for).first.wait_for(state="visible", timeout=timeout)
    page.wait_for_timeout(400)


# ---------------------------------------------------------------- inspect

INSPECT_JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 2 && r.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'; };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim().slice(0, 80);
  const q = s => JSON.stringify(s);
  const rx = s => '/' + s.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&') + '/i';  // icons can add hidden characters to names
  const unique = sel => { try { return document.querySelectorAll(sel).length === 1; } catch { return false; } };
  const out = [];
  const nodes = document.querySelectorAll('a,button,input,select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=switch],[role=combobox],[contenteditable=true]');
  for (const el of nodes) {
    if (!vis(el) || (el.type === 'hidden')) continue;
    const tag = el.tagName.toLowerCase();
    let role = el.getAttribute('role') || ({a: 'link', button: 'button', select: 'combobox', textarea: 'textbox', summary: 'button'})[tag] || '';
    if (tag === 'input') role = ({checkbox: 'checkbox', radio: 'radio', submit: 'button', button: 'button'})[el.type] || 'textbox';
    const label = el.labels && el.labels[0] ? clean(el.labels[0].innerText) : '';
    const name = clean(el.getAttribute('aria-label') || label || (tag === 'input' || tag === 'textarea' ? '' : el.innerText) || el.value || el.getAttribute('placeholder') || el.getAttribute('title') || el.getAttribute('alt'));
    let sel = '';
    if (el.id && unique('#' + CSS.escape(el.id))) sel = '#' + CSS.escape(el.id);
    else if (el.dataset.testid && unique(`[data-testid=${q(el.dataset.testid)}]`)) sel = `[data-testid=${q(el.dataset.testid)}]`;
    else if (el.name && unique(`${tag}[name=${q(el.name)}]`)) sel = `${tag}[name=${q(el.name)}]`;
    else if (name && role) sel = `role=${role}[name=${rx(name)}]`;
    else if (el.getAttribute('placeholder')) sel = `[placeholder=${q(el.getAttribute('placeholder'))}]`;
    const r = el.getBoundingClientRect();
    out.push({role: role || tag, name, placeholder: clean(el.getAttribute('placeholder')), selector: sel,
              box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]});
  }
  const headings = [...document.querySelectorAll('h1,h2,h3')].filter(vis).map(h => h.tagName + ' ' + clean(h.innerText));
  return {title: document.title, url: location.href, headings, elements: out.slice(0, 200)};
}
"""


def cmd_inspect(args):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = new_context(pw, browser, storage_state=args.storage_state, device=args.device, scale=1)
        page = ctx.new_page()
        page.goto(args.url)
        settle(page, args.wait_for)
        info = page.evaluate(INSPECT_JS)
        if args.screenshot:
            Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=args.screenshot, full_page=args.full_page)
        browser.close()
    print(f"Title: {info['title']}\nAddress: {info['url']}")
    if info["headings"]:
        print("Headings:\n  " + "\n  ".join(info["headings"]))
    print("Visible controls (role | name | selector | x,y,w,h in CSS px):")
    for e in info["elements"]:
        name = e["name"] or (f"placeholder={e['placeholder']}" if e["placeholder"] else "")
        print(f"  {e['role']:<9} | {name:<40} | {e['selector'] or '(no stable selector)'} | {','.join(map(str, e['box']))}")
    if args.screenshot:
        print(f"screenshot: {args.screenshot}")


# ---------------------------------------------------------------- login


def cmd_login(args):
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(args.until_url) if args.until_url else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(viewport=None)
        page = ctx.new_page()
        page.goto(args.url)
        print("A browser window is open. Please sign in there, then close the window.", flush=True)
        deadline = time.time() + args.timeout
        saved = False
        try:
            while time.time() < deadline and not page.is_closed():
                ctx.storage_state(path=str(out))
                saved = True
                if pattern and pattern.search(page.url):
                    print(f"Reached {page.url}")
                    break
                page.wait_for_timeout(1000)
            if browser.is_connected():
                ctx.storage_state(path=str(out))
                saved = True
        except PlaywrightError:
            pass  # window/browser closed by the user; the last periodic save stands
        finally:
            if browser.is_connected():
                browser.close()
    if not saved:
        sys.exit("error: browser closed before the session could be saved")
    os.chmod(out, 0o600)
    print(f"Session saved to {out} (contains sign-in cookies: do not share; delete when done)")


# ---------------------------------------------------------------- shoot


def run_action(page, act: dict, base_url: str, plan_dir: Path):
    keys = [k for k in ACTION_KEYS if k in act]
    if len(keys) != 1:
        raise PlanError(f"each action needs exactly one of {', '.join(ACTION_KEYS)}: {act}")
    k = keys[0]
    target = act[k]
    loc = lambda sel: page.locator(sel).first  # noqa: E731
    if k == "click":
        loc(target).click()
    elif k == "dblclick":
        loc(target).dblclick()
    elif k == "fill":
        loc(target).fill(str(act["value"]))
    elif k == "type":
        loc(target).press_sequentially(str(act["value"]), delay=40)
    elif k == "press":
        (loc(act["on"]).press(target) if act.get("on") else page.keyboard.press(target))
    elif k == "select":
        loc(target).select_option(act.get("value") if "value" in act else None, label=act.get("label"))
    elif k == "check":
        loc(target).check()
    elif k == "uncheck":
        loc(target).uncheck()
    elif k == "hover":
        loc(target).hover()
    elif k == "scroll_to":
        loc(target).scroll_into_view_if_needed()
    elif k == "wait_for":
        loc(target).wait_for(state="visible", timeout=act.get("timeout_ms", 15000))
    elif k == "wait_ms":
        page.wait_for_timeout(int(target))
    elif k == "goto":
        page.goto(urljoin(base_url, target))
    elif k == "upload":
        path = Path(act["file"])
        loc(target).set_input_files(str(path if path.is_absolute() else plan_dir / path))
    if k in ("click", "dblclick", "press", "goto"):
        settle(page)


def element_boxes(page, selectors: list, full_page: bool, required: bool, shot: str):
    scroll = page.evaluate("() => [window.scrollX, window.scrollY]") if full_page else (0, 0)
    boxes = []
    for item in selectors:
        sel, label = (item, None) if isinstance(item, str) else (item["selector"], item.get("label"))
        locs = page.locator(sel)
        n = locs.count()
        if n == 0:
            if required:
                raise PlanError(f"shot '{shot}': nothing on the page matches {sel!r}")
            continue
        # blur every match; highlight only the first
        for i in range(n if label is None and not required else 1):
            b = locs.nth(i).bounding_box()
            if b:
                boxes.append((b["x"] + scroll[0], b["y"] + scroll[1], b["width"], b["height"], label))
    return boxes


def cmd_shoot(args):
    plan_path = Path(args.plan).resolve()
    plan_dir = plan_path.parent
    try:
        plan = expand_env(json.loads(plan_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise PlanError(f"{plan_path}: invalid JSON: {e}") from e
    base_url = plan.get("base_url", "")
    outdir = plan_dir / plan.get("outdir", "shots")
    outdir.mkdir(parents=True, exist_ok=True)
    rel = lambda p: (plan_dir / p) if p and not Path(p).is_absolute() else (Path(p) if p else None)  # noqa: E731
    global_blur = plan.get("blur", [])

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=plan.get("headless", True))
        scale = plan.get("device_scale_factor", 2)
        ctx = new_context(pw, browser, viewport=plan.get("viewport"), scale=scale,
                          storage_state=rel(plan.get("storage_state")), device=plan.get("device"),
                          locale=plan.get("locale"))
        if plan.get("device"):
            scale = pw.devices[plan["device"]]["device_scale_factor"]
        page = ctx.new_page()
        try:
            for shot in plan["shots"]:
                name = shot["name"]
                if shot.get("url"):
                    page.goto(urljoin(base_url, shot["url"]))
                    settle(page)
                for act in shot.get("actions", []):
                    run_action(page, act, base_url, plan_dir)
                settle(page, shot.get("wait_for"))
                if shot.get("skip_screenshot"):
                    print(f"done   {name} (no screenshot)")
                    continue
                full_page = bool(shot.get("full_page"))
                hl = shot.get("highlight", [])
                if hl and not full_page:
                    first = hl[0] if isinstance(hl[0], str) else hl[0]["selector"]
                    page.locator(first).first.scroll_into_view_if_needed()
                    page.wait_for_timeout(200)
                raw = outdir / f"{name}.raw.png"
                page.screenshot(path=str(raw), full_page=full_page, caret="hide", animations="disabled")
                to_px = lambda boxes: [(x * scale, y * scale, w * scale, h * scale, *rest) for x, y, w, h, *rest in boxes]  # noqa: E731
                blur_boxes = to_px(element_boxes(page, global_blur + shot.get("blur", []), full_page, False, name))
                hl_boxes = to_px(element_boxes(page, hl, full_page, True, name))
                clip = element_boxes(page, [shot["clip"]], full_page, True, name)[0] if shot.get("clip") else None

                img = Image.open(raw).convert("RGB")
                blur(img, [b[:4] for b in blur_boxes], scale / 2)
                highlight(img, hl_boxes, scale)
                if clip:
                    m = shot.get("clip_margin", 48)  # room for markers beside boxes
                    x, y, w, h, _ = clip
                    img = img.crop((max(0, (x - m) * scale), max(0, (y - m) * scale),
                                    min(img.width, (x + w + m) * scale), min(img.height, (y + h + m) * scale)))
                out = outdir / f"{name}.png"
                img.save(out)
                raw.unlink()
                print(f"saved  {out} ({img.width}x{img.height})")
            if plan.get("save_storage_state"):
                state = rel(plan["save_storage_state"])
                ctx.storage_state(path=str(state))
                os.chmod(state, 0o600)
                print(f"session saved to {state}")
        except (PlaywrightError, KeyError) as e:
            fail = outdir / "_failure.png"
            try:
                page.screenshot(path=str(fail))
            except PlaywrightError:
                pass
            raise PlanError(f"shot '{shot.get('name', '?')}' failed: {e}\npage: {page.url}\nscreen at failure: {fail}") from e
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("--url", required=True)
    i.add_argument("--storage-state")
    i.add_argument("--screenshot")
    i.add_argument("--full-page", action="store_true")
    i.add_argument("--wait-for", help="selector to wait for before reading the page")
    i.add_argument("--device", help='Playwright device name for mobile web, e.g. "iPhone 13"')
    lg = sub.add_parser("login")
    lg.add_argument("--url", required=True)
    lg.add_argument("--out", required=True)
    lg.add_argument("--until-url", help="regex; finish automatically once the address matches")
    lg.add_argument("--timeout", type=int, default=600, help="seconds (default 600)")
    s = sub.add_parser("shoot")
    s.add_argument("plan")
    args = ap.parse_args()
    try:
        {"inspect": cmd_inspect, "login": cmd_login, "shoot": cmd_shoot}[args.cmd](args)
    except PlanError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
