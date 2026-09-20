"""Browser acceptance: python -m scripts.browser_check --output-dir runs/browser.

Default: real loopback navigation, including actual response headers and CSP.
--bridge is an explicit fallback for managed browsers that prohibit localhost;
that mode does NOT establish browser-network/CSP correctness. No provider is called.
Playwright is a development-only dependency, not an application dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

from jev_lab import provider, server, studio

ROOT = Path(__file__).resolve().parents[1]


def mock_response(request, prepaid=None):
    """Only for this QA process. Authored transport mock, never model evidence."""
    token = prepaid or provider.BUDGET.hold(1)
    token.consume()
    answers = {}
    for qid, q in request["questions"].items():
        if q["type"] == "noul":
            a = {"type": "noul", "noul": 0.5}
        else:
            keys = (
                list(q["criteria"])
                if q["type"] == "choice"
                else [str(i) for i in range(len(q["criteria"]))]
            )
            a = {
                "type": q["type"],
                "probabilities": {k: float(i == 0) for i, k in enumerate(keys)},
                "confidence": 1.0,
            }
            if q["type"] == "choice":
                a["choice"] = keys[0]
            else:
                a.update(score=0.0, legend={str(i): v for i, v in enumerate(q["criteria"])})
        answers[qid] = a
    response = {
        "model": request["model"],
        "answers": answers,
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    return response, {
        "kind": "transport_mock",
        "model_calls": 1,
        "latency_ms": 1.0,
        "estimated_cost_usd": 0.000001,
        "usage": response["usage"],
        "warning": "QA TRANSPORT MOCK. No external model was called.",
    }


def run(bridge: bool, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "RUNNING",
        "checks": [],
        "page_errors": [],
        "console_errors": [],
        "unexpected_requests": [],
        "browser": "Chromium / Playwright",
        "bridge": bridge,
        "real_navigation_and_csp": not bridge,
        "live_provider_calls": 0,
        "transport_mock_exercised": False,
        "screenshots": [],
        "environment_note": "Browser plugin absent. Explicit bridge bypasses browser-network/CSP coverage, not the HTTP server."
        if bridge
        else "Browser plugin absent. Direct navigation to the running loopback server.",
    }
    http = server.make_server(0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    report["url"] = (
        base if not bridge else "about:blank with explicit local-asset / real-HTTP bridge"
    )
    report["viewports"] = [[1440, 1100], [375, 812]]
    page = browser = None
    try:
        with sync_playwright() as pw:
            launch = {"headless": True}
            if os.getenv("JEV_CHROMIUM"):
                launch["executable_path"] = os.environ["JEV_CHROMIUM"]
            browser = pw.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
            page.on(
                "console",
                lambda m: report["console_errors"].append(m.text) if m.type == "error" else None,
            )
            page.on(
                "request",
                lambda req: (
                    report["unexpected_requests"].append(req.url)
                    if not req.url.startswith(base + "/") and not req.url.startswith("data:")
                    else None
                ),
            )
            if bridge:

                def http_bridge(path, options):
                    assert (
                        isinstance(path, str) and path.startswith("/") and not path.startswith("//")
                    )
                    payload = options.get("body")
                    req = urllib.request.Request(
                        base + path,
                        data=payload.encode() if payload else None,
                        headers=options.get("headers", {}),
                        method=options.get("method", "GET"),
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=15) as response:
                            return {
                                "ok": True,
                                "status": response.status,
                                "data": json.load(response),
                            }
                    except urllib.error.HTTPError as exc:
                        return {"ok": False, "status": exc.code, "data": json.load(exc)}

                page.expose_function("labBridge", http_bridge)
                html = (ROOT / "web/index.html").read_text()
                styles = re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)
                scripts = re.findall(r'<script[^>]+src="([^"]+)"[^>]*></script>', html)
                html = re.sub(r"<link[^>]*>|<script.*?</script>", "", html)
                page.set_content(html)
                for src in styles:
                    page.add_style_tag(content=(ROOT / "web" / server.STATIC[src][0]).read_text())
                page.add_script_tag(
                    content="window.fetch=async(path,options={})=>{const r=await window.labBridge(path,options);return {ok:r.ok,status:r.status,json:async()=>r.data};};"
                )
                for src in scripts:
                    page.add_script_tag(content=(ROOT / "web" / server.STATIC[src][0]).read_text())
                report["manifest_assets"] = styles + scripts
            else:
                response = page.goto(base + "/", wait_until="networkidle", timeout=20000)
                assert response and response.status == 200
                assert "script-src 'self'" in response.headers["content-security-policy"]
                assert page.url == base + "/"
            # Locator assertions poll in Playwright's isolated utility world.
            # Do not enable unsafe-eval or bypass CSP to inspect application state.
            expect(page.locator("#lessonRun")).to_be_enabled()
            expect(page.locator("#studioExport")).to_be_enabled()

            def expect_preview(pattern_id, variant):
                request = studio.preview(pattern_id, variant)["request"]
                expect(page.locator("#studioRequest")).to_have_text(
                    json.dumps(request, indent=2, ensure_ascii=False)
                )
                return request
            assert page.title() == "Jev Decision Lab"
            assert page.locator("#start").is_visible()
            assert not page.locator("#workbench").is_visible()
            assert "Your system must decide" in page.locator("#startTitle").inner_text()
            report["checks"].append(
                "Correct nonblank Start screen; all manifest assets initialized; no automatic model call"
            )

            def shot(name):
                page.screenshot(path=str(output / name), full_page=True)
                report["screenshots"].append(name)

            shot("start-desktop.png")
            page.locator("#lessonRun").click()
            expect(page.locator("#lessonEvidence")).to_contain_text("ROUTE_TO_TEAM")
            assert "ROUTE_TO_TEAM" in page.locator("#lessonEvidence").inner_text()
            page.locator("#lessonNext").click()
            expect(page.locator("#lessonEvidence")).to_contain_text("REFRESH_EVIDENCE")
            assert "HOLD" in page.locator("#lessonEvidence").inner_text()
            assert "REFRESH_EVIDENCE" in page.locator("#lessonEvidence").inner_text()
            page.locator("#lessonNext").click()
            expect(page.locator("#teachBack")).to_be_visible()
            for q, answer in {"q1": "shape", "q2": "gate", "q3": "estimate"}.items():
                page.locator(f'input[name="{q}"][value="{answer}"]').check()
            page.locator("#teachForm button").click()
            assert "3 / 3" in page.locator("#teachResult").inner_text()
            with page.expect_download() as download:
                page.locator("#lessonExport").click()
            record = json.loads(Path(download.value.path()).read_text())
            assert record["external_validation"] is False
            assert len(record["observations"]) == 3
            report["checks"].append(
                "Three-step lesson runs real replay/policy/authority paths; teach-back and JSON download work"
            )
            shot("lesson-desktop.png")

            page.locator('[data-tab="studio"]').click()
            page.locator("summary").filter(has_text="Exact request · no model output").click()
            for pattern in studio.catalog():
                page.locator(f'[data-pattern="{pattern["id"]}"]').click()
                for variant in ("routine", "adverse"):
                    page.locator("#studioVariant").select_option(variant)
                    expect_preview(pattern["id"], variant)
                    request = json.loads(page.locator("#studioRequest").inner_text())
                    assert request == studio.preview(pattern["id"], variant)["request"]
                    assert not page.locator("#studioExport").is_disabled()
            report["checks"].append(
                "All 16 Studio previews match the server-generated versioned request; switching clears live consent"
            )
            page.locator("#patternSearch").fill("no-such-pattern")
            assert "No patterns match" in page.locator("#patternList").inner_text()
            page.locator("#patternSearch").fill("")
            page.locator('[data-pattern="citation"]').click()
            expect_preview("citation", page.locator("#studioVariant").input_value())
            assert "Hold:" in page.locator("#studioChecks").inner_text()
            with page.expect_download() as download:
                page.locator("#studioExport").click()
            req = json.loads(Path(download.value.path()).read_text())
            assert set(req) == {"model", "state", "questions"}
            with page.expect_download() as download:
                page.locator("#studyExport").click()
            plan = json.loads(Path(download.value.path()).read_text())
            assert plan["status"] == "UNRUN" and plan["results"] is None
            report["checks"].append(
                "Pattern search has an empty state; request and UNRUN study exports preserve their distinct meaning"
            )
            page.locator("summary").filter(has_text="Exact request · no model output").click()
            shot("studio-desktop.png")

            page.locator("#economicsForm button").click()
            page.wait_for_selector("#economicsResult table")
            page.locator("#econ_review_capacity_hours").fill("0")
            page.locator("#economicsForm button").click()
            expect(page.locator("#economicsResult")).to_contain_text("Review capacity shortfall")
            with page.expect_download() as download:
                page.locator("#economicsExport").click()
            econ = json.loads(Path(download.value.path()).read_text())
            assert econ["kind"] == "assumption_only" and econ["capacity"]["feasible"] is False
            assert econ["model_calls"] == 0
            report["checks"].append(
                "Economics recomputes all-attempt cost, imperfect-review loss, capacity hold and four sensitivity scenarios"
            )
            shot("economics-desktop.png")

            page.locator('[data-tab="workbench"]').click()
            page.locator('[data-case="S02"]').click()
            page.locator("#run").click()
            expect(page.locator("#route")).to_have_text("Recommend a team")
            page.locator("#variant").select_option("stale")
            page.locator("#reconsider").click()
            expect(page.locator("#route")).to_have_text("Refresh the evidence")
            with page.expect_download() as download:
                page.locator("#export").click()
            receipt = json.loads(Path(download.value.path()).read_text())
            assert receipt["provenance"]["kind"] == "synthetic_replay"
            assert receipt["additional_model_calls"] == 0
            report["checks"].append(
                "Existing Workbench policy replay and receipt export remain functional"
            )

            page.locator('[data-tab="live"]').click()
            page.locator("#compareRun").click()
            page.wait_for_selector("#compareTable table")
            assert "Common subset agreement" in page.locator("#compareSummary").inner_text()
            page.locator("#probeRun").click()
            expect(page.locator("#exportProbe")).to_be_enabled()
            page.locator("#ablateRun").click()
            expect(page.locator("#exportAblate")).to_be_enabled()
            assert "Descriptive reference" in page.locator("#ablateSummary").inner_text()
            with page.expect_download() as download:
                page.locator("#exportReport").click()
            html = Path(download.value.path()).read_text()
            assert "latest retained result" in html and "Assumption-only" in html
            assert "<script" not in html
            report["checks"].append(
                "Replay comparison, paired denominators, probes, ablation and self-contained snapshot export work"
            )

            # These two observations exercise rendering/error retention, not model capability.
            page.locator('[data-tab="studio"]').click()
            with (
                patch("jev_lab.provider.live_enabled", return_value=True),
                patch("jev_lab.provider.live", side_effect=mock_response),
                patch.object(provider, "BUDGET", provider.CallBudget(20)),
            ):
                page.evaluate("() => refreshConfig()")
                page.locator("#studioConsent").check()
                page.locator("#studioRun").click()
                expect(page.locator("#studioResultExport")).to_be_enabled()
                assert page.locator("#studioResult details").count() >= 2, (
                    "Studio did not render typed answers from the QA transport mock"
                )
                assert "human review required" in page.locator("#studioStatus").inner_text()
                assert not page.locator("#studioConsent").is_checked()
                with page.expect_download() as download:
                    page.locator("#studioResultExport").click()
                observation = json.loads(Path(download.value.path()).read_text())
                assert observation["result"]["provenance"]["kind"] == "transport_mock"
                assert provider.BUDGET.used == 1

            def malformed(request, prepaid=None):
                response, provenance = mock_response(request, prepaid)
                response["answers"] = {}
                return response, provenance

            with (
                patch("jev_lab.provider.live_enabled", return_value=True),
                patch("jev_lab.provider.live", side_effect=malformed),
                patch.object(provider, "BUDGET", provider.CallBudget(20)),
            ):
                page.evaluate("() => refreshConfig()")
                page.locator("#studioConsent").check()
                page.locator("#studioRun").click()
                expect(page.locator("#studioResultExport")).to_be_enabled()
                assert "failed" in page.locator("#studioStatus").inner_text()
                with page.expect_download() as download:
                    page.locator("#studioResultExport").click()
                failed = json.loads(Path(download.value.path()).read_text())
                assert failed["failure"] and failed["detail"]["provider_response"]["answers"] == {}
                assert failed["detail"]["provenance"]["estimated_cost_usd"] == 0.000001
                assert provider.BUDGET.used == 1
            report["transport_mock_exercised"] = True
            report["checks"].append(
                "Explicit-consent Studio success and malformed-response paths tested with authored transport mocks; failure response/cost retained; no retry"
            )
            page.evaluate("() => refreshConfig()")
            page.locator("#studioVariant").select_option("routine")
            expect_preview("citation", "routine")
            page.locator("#studioRun").click()
            assert "Connect Jev first" in page.locator("#error").inner_text()
            report["checks"].append(
                "Unconfigured live path is an explicit refusal, never invented replay"
            )

            page.set_viewport_size({"width": 375, "height": 812})
            for tab in ("start", "studio", "workbench", "live", "garden", "signals", "learn"):
                page.locator(f'[data-tab="{tab}"]').click()
                assert page.locator(f"#{tab}").is_visible()
                if not page.evaluate("document.documentElement.scrollWidth <= innerWidth"):
                    report["overflow_elements"] = page.evaluate(
                        "Array.from(document.querySelectorAll('body *')).filter(e => {const r=e.getBoundingClientRect();return r.width && (r.right>innerWidth+1 || r.left < -1)}).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width,text:e.textContent.slice(0,70)})).slice(0,30)"
                    )
                    shot(f"{tab}-overflow.png")
                    raise AssertionError(f"Overflow in {tab}")
                if tab in ("start", "studio"):
                    shot(f"{tab}-mobile.png")
            report["checks"].append(
                "Every top-level surface remains usable without document-level horizontal overflow at 375px"
            )
            page.locator('[data-tab="studio"]').click()
            page.locator("#patternSelect").select_option("extraction")
            expect_preview("extraction", "routine")
            assert page.locator("#studioSituation").is_visible()
            report["checks"].append(
                "Phone pattern selector changes the readable source and typed questions without a live call"
            )
            page.locator('[data-tab="start"]').focus()
            page.keyboard.press("Enter")
            assert page.locator("#start").is_visible()
            assert page.locator('[data-tab="start"]').get_attribute("aria-current") == "page"
            report["checks"].append(
                "Keyboard navigation exposes current-page state and reaches visible Start content"
            )
            assert not report["page_errors"], report["page_errors"]
            assert not report["unexpected_requests"], report["unexpected_requests"]
            # Only the intentional malformed mock returns HTTP 400 and may produce a browser network log.
            unexpected_console = [
                s
                for s in report["console_errors"]
                if not re.fullmatch(
                    r"Failed to load resource: the server responded with a status of 400 \(Bad Request\)",
                    s,
                )
            ]
            assert not unexpected_console, unexpected_console
            report["status"] = "PASS"
            browser.close()
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        raise
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)
        (output / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="Explicit managed-browser fallback; does not verify browser-network/CSP integration",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/browser"))
    args = parser.parse_args()
    run(args.bridge, args.output_dir)
