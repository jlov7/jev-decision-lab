"""Chromium interaction smoke test for development QA. Needs Playwright (`uv run --with playwright`).

Set JEV_CHROMIUM to a Chromium executable to use one you already have; otherwise Playwright's own
browser is used. Prints a summary and exits non-zero on any failed check or page error."""

import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

from jev_lab.server import make_server

root = Path(__file__).resolve().parents[1]
http = make_server(0)
thread = threading.Thread(target=http.serve_forever, daemon=True)
thread.start()
checks, errors = [], []
try:
    with sync_playwright() as p:
        launch = {"headless": True}
        if os.getenv("JEV_CHROMIUM"):
            launch["executable_path"] = os.environ["JEV_CHROMIUM"]
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(str(e)))

        # Managed Chromium blocks loopback navigation. Do not disable its policy.
        # Render local assets and bridge fetch to the actual loopback HTTP server.
        # This checks UI + server behavior, but not browser-network/CSP integration.
        def bridge(path, options):
            body = options.get("body")
            req = urllib.request.Request(
                f"http://127.0.0.1:{http.server_port}" + path,
                data=body.encode() if body else None,
                headers=options.get("headers", {}),
                method=options.get("method", "GET"),
            )
            try:
                with urllib.request.urlopen(req) as response:
                    return {"ok": True, "status": response.status, "data": json.load(response)}
            except urllib.error.HTTPError as exc:
                return {"ok": False, "status": exc.code, "data": json.load(exc)}

        page.expose_function("labBridge", bridge)
        html = (root / "web/index.html").read_text()
        html = re.sub(r"<link[^>]*>", "", html)
        html = re.sub(r"<script.*?</script>", "", html)
        page.set_content(html)
        page.add_style_tag(content=(root / "web/style.css").read_text())
        page.add_script_tag(
            content="window.fetch = async (path, options = {}) => { const r = await window.labBridge(path, options); return {ok:r.ok, status:r.status, json:async()=>r.data}; };"
        )
        page.add_script_tag(content=(root / "web/app.js").read_text())
        page.add_script_tag(content=(root / "web/live.js").read_text())
        page.wait_for_selector('[data-case="S02"]')
        assert page.title() == "Jev Decision Lab"
        page.locator('[data-case="S02"]').click()
        page.locator("#run").click()
        page.wait_for_function(
            "document.getElementById('route').textContent === 'Recommend a team'"
        )
        checks.append("Replay run changes the recommendation")
        page.locator("#answers details").nth(1).locator("summary").click()
        assert page.locator("#answers meter").count() > 10
        page.locator("#action").click()
        page.wait_for_function(
            "document.getElementById('actionResult').textContent.includes('SIMULATED_RECOMMENDATION')"
        )
        page.locator("#approval_current").uncheck()
        page.locator("#action").click()
        page.wait_for_function(
            "document.getElementById('actionResult').textContent.includes('HOLD')"
        )
        checks.append("Before-action approval revocation blocks the simulation")
        page.locator("#variant").select_option("stale")
        page.locator("#reconsider").click()
        page.wait_for_function(
            "document.getElementById('route').textContent === 'Refresh the evidence'"
        )
        checks.append("Policy replay changes the route with zero new model calls")
        page.screenshot(path=str(root / "evidence/desktop.png"), full_page=True)
        with page.expect_download() as download:
            page.locator("#export").click()
        assert download.value.suggested_filename.endswith("receipt.json")
        checks.append("Receipt export returns a JSON download")
        page.locator('[data-tab="garden"]').click()
        page.locator("#task").select_option("calculate")
        page.locator("#gardenRun").click()
        page.wait_for_function(
            "document.getElementById('gardenResult').textContent.includes('deterministic')"
        )
        checks.append("Model garden maps exact calculation to code, not Jev")
        page.locator('[data-tab="signals"]').click()
        assert page.locator(".signal").count() == 8
        page.locator("#asOf").fill("2026-09-17")
        page.locator("#asOf").dispatch_event("change")
        assert page.locator(".signal").count() == 11
        checks.append("As-of chronology filters dates without claiming tracker ingestion")
        page.locator('[data-tab="learn"]').click()
        page.locator("#evaluate").click()
        page.wait_for_selector("#evalResults table")
        assert "authored fixtures" in page.locator("#evalResults").inner_text()
        checks.append("Evaluation labels all results as authored teaching fixtures")
        page.locator('[data-tab="workbench"]').click()
        page.locator("#mode").select_option("live")
        page.locator("#run").click()
        page.wait_for_selector("#error:not([hidden])")
        assert "not configured" in page.locator("#error").inner_text()
        checks.append("Unconfigured live mode is an explicit error, not a replay fallback")
        page.locator("#connect").click()
        assert page.locator("#setup").is_visible()
        page.locator("#closeSetup").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#mode").select_option("replay")
        page.locator('[data-case="S04"]').click()
        page.locator("#run").click()
        page.wait_for_function(
            "document.getElementById('route').textContent !== 'Ready to inspect'"
        )
        page.screenshot(path=str(root / "evidence/mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        checks.append("390px mobile viewport has no document-level horizontal overflow")
        assert not errors, errors
        browser.close()
finally:
    http.shutdown()
    http.server_close()
    thread.join(timeout=2)
report = {
    "browser": "Playwright / system Chromium",
    "fallback_reason": "Browser plugin absent; managed Chromium blocks loopback navigation. Local-asset rendering with a bridge to the real HTTP server was used; browser-network/CSP integration remains untested.",
    "viewports": [[1440, 1100], [390, 844]],
    "checks": checks,
    "page_errors": errors,
    "live_jev_executed": False,
    "status": "PASS",
}
print(json.dumps(report, indent=2))
sys.exit(1 if errors or not all(c.get("ok", True) for c in checks if isinstance(c, dict)) else 0)
print(json.dumps(report, indent=2))
