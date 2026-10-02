#!/usr/bin/env python3
"""Exercise the built site and capture host-only visual evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urljoin
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
        executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
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
        assert page.locator("[data-known-applications] img").count() == 2
        for measured_image in page.locator("[data-known-applications] img").all():
            measured_image.scroll_into_view_if_needed()
            page.wait_for_function("image => image.complete && image.naturalWidth > 0", arg=measured_image.element_handle())
        assert "WXJC" in page.locator("#content").inner_text()
        assert "Five known BLE packets" in page.locator("#content").inner_text()
        # The published demo must show values from its linked physical receipt,
        # load its actual capture, and expose the matching verified recovery.
        demo = page.locator(".interactive-demo")
        assert demo.count() == 1
        demo.scroll_into_view_if_needed()
        metrics_url = urljoin(base, demo.get_by_role("link", name="Session metrics →", exact=True).get_attribute("href"))
        restoration_url = urljoin(base, demo.get_by_role("link", name="Restoration receipt →", exact=True).get_attribute("href"))
        details_url = urljoin(base, demo.get_by_role("link", name="Setup, recovery and command details →", exact=True).get_attribute("href"))
        proof = browser.new_page()
        proof.on("pageerror", lambda error: errors.append(str(error)))
        proof.on("response", lambda response: failures.append(response.url) if response.status >= 400 and response.url.startswith(base) else None)
        try:
            assert proof.goto(metrics_url, wait_until="networkidle").status == 200
            metrics = json.loads(proof.locator(".ev-text").inner_text())
            assert metrics["status"] == "completed"
            assert metrics["demo_duration_gate_passed"] is True
            assert metrics["settings"]["seconds_requested"] >= 60
            assert metrics["elapsed_seconds"] >= metrics["settings"]["seconds_requested"]
            assert metrics["end_report"][4] >= metrics["settings"]["seconds_requested"] * 1000000
            facts = demo.locator(".fact-strip strong").all_inner_texts()
            assert facts == [f'{metrics["frames"]:,}', f'{metrics["elapsed_seconds"]:.3f} s',
                             f'{metrics["settings"]["ffts_per_frame"]} averaged',
                             f'{metrics["nominal_coverage_fraction"] * 100:.3f}%'], facts
            assert proof.goto(restoration_url, wait_until="networkidle").status == 200
            restoration = json.loads(proof.locator(".ev-text").inner_text())
            assert restoration["verified"] is True
            assert restoration["full_readback_bytes"] == 4194304
            assert restoration["full_readback_sha256"] == restoration["baseline_sha256"]
            assert restoration["boot"]["power_cycle_proven"] is False
            assert proof.goto(details_url, wait_until="networkidle").status == 200
            assert "demo:esp:restore" in proof.locator("#content").inner_text()
        finally:
            proof.close()
        capture = demo.locator("img")
        assert capture.count() == 1
        assert "actual" in capture.get_attribute("alt").lower()
        capture.scroll_into_view_if_needed()
        page.wait_for_function("image => image.complete && image.naturalWidth > 0", arg=capture.element_handle())
        completed = page.request.get(urljoin(base, demo.get_by_role("link", name="See the completed display →", exact=True).get_attribute("href")))
        assert completed.status == 200 and completed.headers["content-type"].startswith("image/png")
        command = demo.locator(".demo-command").inner_text()
        assert "nix develop --command task demo:esp" in command
        assert "--output docs/evidence/esp-demo-next" in command and "--private .scratch/esp-demo-next" in command
        assert "uncalibrated" in demo.inner_text() and "continuous reception" in demo.inner_text()
        demo.screenshot(path=str(output / "interactive-demo.png"))
        page.screenshot(path=str(output / "overview-desktop.png"), full_page=True)
        theme = page.locator("html").get_attribute("data-theme")
        page.locator("#theme-toggle").click()
        assert page.locator("html").get_attribute("data-theme") != theme
        page.locator("#theme-toggle").click()
        assert page.goto(base + "work/", wait_until="networkidle").status == 200
        assert page.locator("[data-work-id]").count() == 8
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
        # Archival must preserve the original stable proposal URL.
        for archived in (
            "the-board-captures-repeatable-radio-snapshots",
            "the-board-can-be-restored-after-an-sdr-trial",
            "the-two-receivers-have-a-measured-division-of-labor",
        ):
            page.goto(base + "work/?work=" + archived, wait_until="networkidle")
            page.locator("#work-detail-dialog[open]").wait_for()
            assert "archived" in page.locator("#work-detail-content").inner_text().lower()
            page.keyboard.press("Escape")
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
        "checks": ["desktop and mobile navigation", "no horizontal page overflow", "capture budget calculator", "theme toggle", "eight proposal cards", "proposal deep link", "gallery image loaded", "dialog focus restored", "boot evidence link", "actual BLE/RDS images loaded", "verified demo metrics, receipt links and actual images", "archived proposal stable URL", "no page errors or local HTTP failures"],
        "result": "passed"
    }, indent=2) + "\n")
    print("Browser checks passed; host screenshots recorded at", output)

if __name__ == "__main__":
    main()
