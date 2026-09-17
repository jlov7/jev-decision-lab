"""Native TypeSafe transport; no automatic retries and no silent replay fallback."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from . import __version__
from .engine import load

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
PRICE_PER_MILLION_INPUT = 0.042
MAX_INPUT_BYTES = 16000  # Lab limit, not a provider context-window claim.
USER_AGENT = f"jev-decision-lab/{__version__}"
HTTP_ERROR_BODY_LIMIT = 2000


class Prepaid:
    """Slots already counted against the process cap. live() consumes one per send."""

    def __init__(self, n: int):
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("Prepaid reservation must cover at least one attempt")
        self.left, self.lock = n, threading.Lock()

    def consume(self) -> None:
        with self.lock:
            if self.left < 1:
                raise RuntimeError(
                    "Prepaid attempt reservation is exhausted. Nothing extra was sent."
                )
            self.left -= 1


class CallBudget:
    def __init__(self, limit: int = 20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Live call limit must be an integer from 1 to 100")
        self.limit, self.used, self.lock = limit, 0, threading.Lock()

    def remaining(self) -> int:
        with self.lock:
            return self.limit - self.used

    def reserve(self, n: int = 1) -> None:
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("Reservation size must be a positive integer")
        with self.lock:
            left = self.limit - self.used
            if n > left:
                raise RuntimeError(
                    f"Need {n} attempt slots but {left} remain in this process. Nothing was sent. "
                    "This is not an account-wide billing cap."
                )
            self.used += n

    def hold(self, n: int) -> Prepaid:
        """Atomically reserve n attempts so a burst or compare cannot send a partial batch."""
        self.reserve(n)
        return Prepaid(n)


BUDGET = CallBudget(int(os.getenv("JEV_MAX_LIVE_CALLS", "20")))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward bearer credentials to another location.


def replay(case_id: str) -> dict:
    try:
        return load("replay")[case_id]
    except KeyError as exc:
        raise ValueError("No teaching fixture for this case") from exc


def live_enabled() -> bool:
    return os.getenv("JEV_ALLOW_LIVE") == "1" and bool(os.getenv("TYPESAFE_API_KEY"))


def _redact(text: str) -> str:
    key = os.environ.get("TYPESAFE_API_KEY") or ""
    if key:
        text = text.replace(key, "[redacted]")
    return text


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    """Surface 422 field errors. Never echo a 401 body (it can contain the key)."""
    try:
        raw = exc.read(HTTP_ERROR_BODY_LIMIT + 1)
    except Exception:
        return ""
    finally:
        try:
            exc.close()
        except Exception:
            pass
    if exc.code not in {400, 422} or not raw:
        return ""
    text = (
        _redact(raw[:HTTP_ERROR_BODY_LIMIT].decode("utf-8", "replace")).strip().replace("\n", " ")
    )
    if not text:
        return ""
    return f" Provider said: {text[:500]}"


def live(payload: dict, prepaid: Prepaid | None = None) -> tuple[dict, dict]:
    if not live_enabled():
        raise PermissionError(
            "Live mode disabled. Set TYPESAFE_API_KEY and JEV_ALLOW_LIVE=1 in the server terminal."
        )
    body = json.dumps(payload, allow_nan=False).encode()
    if len(body) > MAX_INPUT_BYTES:
        raise ValueError("Request exceeds the lab 16,000-byte ceiling. Nothing was sent.")
    if prepaid is None:
        prepaid = BUDGET.hold(1)
    prepaid.consume()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + os.environ["TYPESAFE_API_KEY"],
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=15) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError("Response exceeds lab ceiling")
            result = json.loads(raw)
    except urllib.error.HTTPError as exc:
        reasons = {
            401: "API key rejected",
            403: "Account access denied",
            422: "Request/model contract rejected",
            429: "Rate limited; retry deliberately later",
            529: "Provider overloaded",
        }
        detail = _http_error_detail(exc)
        raise RuntimeError(
            f"TypeSafe HTTP {exc.code}: {reasons.get(exc.code, 'request failed')}.{detail} "
            "No replay fallback was used."
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError(
            "Provider request failed or timed out. Billing may be unknown. No retry or replay fallback was used."
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Provider returned invalid JSON. No replay fallback was used.") from None
    elapsed = (time.perf_counter() - started) * 1000
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    tokens = usage.get("input_tokens")
    estimated = (
        tokens / 1_000_000 * PRICE_PER_MILLION_INPUT
        if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0
        else None
    )
    return result, {
        "kind": "live_typesafe",
        "model_calls": 1,
        "latency_ms": round(elapsed, 2),
        "usage": usage,
        "estimated_cost_usd": estimated,
        "price_per_million_input_usd": PRICE_PER_MILLION_INPUT,
        "price_as_of": "2026-09-17",
        "warning": "Estimated from reported usage and dated public price, not an invoice. Client latency includes network time.",
    }
