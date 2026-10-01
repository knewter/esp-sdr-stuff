#!/usr/bin/env python3
"""Exercise the built site and capture host-only visual evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:4321")
    parser.add_argument("--output", default="test-results/browser")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/") + "/"
    errors, failures = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: failures.append(response.url) if response.status >= 400 and response.url.startswith(base) else None)
        assert page.goto(base, wait_until="networkidle").status == 200
        revision = page.request.get(base + "revision.json").json()["revision"]
        page.evaluate("document.fonts.ready")
        assert page.locator("#capture-duration").inner_text() == "0.205 ms"
        page.locator("#sample-rate").select_option("16")
        assert page.locator("#capture-duration").inner_text() == "1.024 ms"
        page.locator("#sample-rate").select_option("80")
        page.screenshot(path=str(output / "overview-desktop.png"), full_page=True)
        theme = page.locator("html").get_attribute("data-theme")
        page.locator("#theme-toggle").click()
        assert page.locator("html").get_attribute("data-theme") != theme
        page.locator("#theme-toggle").click()
        assert page.goto(base + "work/", wait_until="networkidle").status == 200
        assert page.locator("[data-work-id]").count() == 7
        trigger = page.locator("[data-work-id]").first
        item = trigger.get_attribute("data-work-id")
        trigger.click()
        page.locator("#work-detail-dialog[open]").wait_for()
        assert item in page.url
        page.screenshot(path=str(output / "proposal-dialog.png"))
        page.locator("#work-detail-content .media-open").first.click()
        page.locator("#work-media-dialog[open]").wait_for()
        page.wait_for_function("document.querySelector('#media-image').complete && document.querySelector('#media-image').naturalWidth > 0")
        page.screenshot(path=str(output / "design-gallery.png"))
        page.locator("#media-close").click()
        page.locator("#work-detail-close").click()
        assert not page.locator("#work-detail-dialog").evaluate("element => element.open")
        assert page.evaluate("document.activeElement.dataset.workId") == item
        # Reopening a shared URL restores proposal state.
        page.goto(base + "work/?work=" + item, wait_until="networkidle")
        page.locator("#work-detail-dialog[open]").wait_for()
        page.keyboard.press("Escape")
        for route in ("compare/", "fpga/", "sources/", "ledger/", "evidence/"):
            assert page.goto(base + route, wait_until="networkidle").status == 200
        page.goto(base + "evidence/docs-evidence-board-identification-readme-md/", wait_until="networkidle")
        page.get_by_role("link", name="Boot log", exact=True).click()
        assert "hello_world" in page.locator(".ev-text").inner_text()
        for route in ("", "work/", "compare/", "fpga/"):
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base + route, wait_until="networkidle")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), route
            if not route:
                page.screenshot(path=str(output / "overview-mobile.png"), full_page=True)
        browser.close()
    assert not errors, errors
    assert not failures, failures
    (output / "capture.json").write_text(json.dumps({
        "captured": datetime.now(timezone.utc).isoformat(), "url": base,
        "source_revision": revision,
        "evidence_class": "Host browser capture; no hardware reception measured",
        "checks": ["desktop and mobile navigation", "no horizontal page overflow", "capture budget calculator", "theme toggle", "seven proposal cards", "proposal deep link", "gallery image loaded", "dialog focus restored", "boot evidence link", "no page errors or local HTTP failures"],
        "result": "passed"
    }, indent=2) + "\n")
    print("Browser checks passed; host screenshots recorded at", output)

if __name__ == "__main__":
    main()
