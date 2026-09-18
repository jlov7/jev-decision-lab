"""Loopback teaching server. Never expose this stdlib server to the internet."""

from __future__ import annotations

import json
import secrets
import sys
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import engine, llm_arm, metrics, provider, showcase, strategy

TOKEN = secrets.token_urlsafe(32)
RECEIPTS: OrderedDict[str, dict] = OrderedDict()
LOCK = threading.Lock()
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/live.js": ("live.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/live.css": ("live.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/favicon.ico": ("favicon.svg", "image/svg+xml"),
}
FIELDS = {
    "/api/run": {"case_id", "mode", "threshold", "consent"},
    "/api/reconsider": {"receipt_id", "threshold", "variant"},
    "/api/action-preview": {"receipt_id", "current"},
    "/api/garden": {"task", "allow_cloud", "consequence_high"},
    "/api/evaluate": set(),
    "/api/burst": {"mode", "consent", "case_ids", "threshold"},
    "/api/playground": {"state", "questions", "consent"},
    "/api/compare": {"arms", "case_ids", "consent"},
    "/api/receipt": {"receipt_id"},
}


def store(receipt: dict) -> dict:
    key = secrets.token_urlsafe(16)
    with LOCK:
        RECEIPTS[key] = receipt
        while len(RECEIPTS) > 200:
            RECEIPTS.popitem(last=False)
    return dict(receipt, receipt_id=key)


def lookup(key) -> dict:
    if not isinstance(key, str):
        raise ValueError("A server-issued receipt ID is required")
    with LOCK:
        result = RECEIPTS.get(key)
    if result is None:
        raise ValueError("Receipt expired or unknown. Run the case again.")
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # No persisted request content, keys or model results.

    def failure(self, status: int, exc: BaseException) -> None:
        """One structured line per failed request: path, status, error class and message.

        Never the body, the key or a model answer. Provider messages are already redacted."""
        line = {
            "event": "request_failed",
            "path": urlparse(self.path).path,
            "status": status,
            "error": type(exc).__name__,
            "message": str(exc)[:300] if status != 500 else "unexpected local error",
        }
        print(json.dumps(line), file=sys.stderr, flush=True)

    def origin_allowed(self) -> bool:
        hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (
            origin is None or origin in {"http://" + h for h in hosts}
        )

    def send(self, status: int, value, kind="application/json; charset=utf-8"):
        body = (
            json.dumps(value, allow_nan=False).encode()
            if kind.startswith("application/json")
            else value
        )
        self.send_response(status)
        for key, val in {
            "Content-Type": kind,
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        }.items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.origin_allowed():
            return self.send(403, {"error": "Local same-origin access only"})
        path = urlparse(self.path).path
        if path == "/api/config":
            return self.send(
                200,
                {
                    "session_token": TOKEN,
                    "live_enabled": provider.live_enabled(),
                    "live_attempts": provider.BUDGET.used,
                    "live_attempt_limit": provider.BUDGET.limit,
                    "model": engine.request_for(engine.cases()[0])["model"],
                    "price_per_million_input": provider.PRICE_PER_MILLION_INPUT,
                    "price_as_of": "2026-09-17",
                    "compare_enabled": llm_arm.live_enabled(),
                    "compare_model": llm_arm.model_name(),
                    "compare_sdk_available": llm_arm.sdk_available(),
                    "compare_attempts": llm_arm.BUDGET.used,
                    "compare_attempt_limit": llm_arm.BUDGET.limit,
                    "arms": list(showcase.adapters.ARM_NAMES),
                    "lab_version": provider.USER_AGENT.rsplit("/", 1)[-1],
                    "http_body_limit": showcase.MAX_HTTP_BODY,
                    "provider_input_limit": provider.MAX_INPUT_BYTES,
                },
            )
        if path == "/api/cases":
            labels = engine.load("labels")
            cases = []
            for case in engine.cases():
                row = dict(case)
                label = labels.get(case["id"], {})
                row["teaching_note"] = label.get("teaching_note")
                row["planted_error"] = bool(label.get("planted_error"))
                cases.append(row)
            return self.send(200, {"cases": cases, "packs": engine.load("packs")})
        if path == "/api/signals":
            return self.send(200, engine.load("signals"))
        if path in STATIC:
            filename, kind = STATIC[path]
            return self.send(200, (engine.ROOT / "web" / filename).read_bytes(), kind)
        self.send(404, {"error": "Not found"})

    def do_POST(self):
        if not self.origin_allowed() or not secrets.compare_digest(
            self.headers.get("X-Lab-Token", ""), TOKEN
        ):
            return self.send(403, {"error": "A same-origin lab session token is required"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Use application/json"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= showcase.MAX_HTTP_BODY:
                return self.send(413, {"error": "Invalid or oversized request body"})
            self.connection.settimeout(10)
            body = json.loads(self.rfile.read(length))
            self.connection.settimeout(None)
            path = urlparse(self.path).path
            if path not in FIELDS:
                return self.send(404, {"error": "Not found"})
            if not isinstance(body, dict) or set(body) - FIELDS[path]:
                raise ValueError(
                    "Unexpected request fields; arbitrary state and credentials are not accepted"
                )
            if path == "/api/run":
                return self.send(
                    200,
                    store(
                        engine.run(
                            body.get("case_id"),
                            body.get("mode", "replay"),
                            body.get("threshold", 0.85),
                            body.get("consent", False),
                        )
                    ),
                )
            if path == "/api/reconsider":
                return self.send(
                    200,
                    store(
                        engine.reconsider(
                            lookup(body.get("receipt_id")),
                            body.get("threshold", 0.85),
                            body.get("variant", "original"),
                        )
                    ),
                )
            if path == "/api/action-preview":
                return self.send(
                    200,
                    strategy.action_preview(
                        lookup(body.get("receipt_id")), body.get("current", {})
                    ),
                )
            if path == "/api/garden":
                return self.send(
                    200,
                    strategy.garden(
                        body.get("task"), body.get("allow_cloud"), body.get("consequence_high")
                    ),
                )
            if path == "/api/receipt":
                stored = lookup(body.get("receipt_id"))
                return self.send(200, dict(stored, receipt_id=body.get("receipt_id")))
            if path == "/api/burst":
                ids = body.get("case_ids") or [c["id"] for c in engine.cases()]
                if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                    raise ValueError("case_ids must be a list of case id strings")
                result = showcase.publish_burst(
                    showcase.burst(
                        ids,
                        body.get("mode", "replay"),
                        body.get("consent", False),
                        body.get("threshold", 0.85),
                    ),
                    store,
                )
                return self.send(200, result)
            if path == "/api/playground":
                return self.send(
                    200,
                    showcase.playground(
                        body.get("state"), body.get("questions"), body.get("consent", False)
                    ),
                )
            if path == "/api/compare":
                ids = body.get("case_ids") or []
                if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                    raise ValueError("case_ids must be a list of case id strings")
                return self.send(
                    200, showcase.compare(body.get("arms"), ids, body.get("consent", False))
                )
            return self.send(
                200,
                metrics.evaluate(
                    [engine.run(c["id"]) for c in engine.cases()], engine.load("labels")
                ),
            )
        except PermissionError as exc:
            self.failure(403, exc)
            self.send(403, {"error": str(exc)})
        except engine.LiveValidationError as exc:
            self.failure(400, exc)
            self.send(
                400,
                {
                    "error": str(exc),
                    "provider_response": exc.response,
                    "provenance": exc.provenance,
                    "retained": "The provider answered; the answer broke the contract. Nothing was retried.",
                },
            )
        except (ValueError, TypeError, KeyError) as exc:
            self.failure(400, exc)
            self.send(
                400,
                {
                    "error": str(exc)
                    if isinstance(exc, ValueError)
                    else "Invalid request or provider contract"
                },
            )
        except RuntimeError as exc:
            self.failure(502, exc)
            self.send(502, {"error": str(exc)})
        except Exception as exc:
            self.failure(500, exc)
            self.send(
                500,
                {
                    "error": "Unexpected local error. No automatic retry or replay fallback was used."
                },
            )


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port: int = 8765) -> None:
    http = make_server(port)
    print(f"Jev Decision Lab: http://127.0.0.1:{http.server_port}", flush=True)
    print("Synthetic replay is the default. Live requests require explicit consent.", flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
