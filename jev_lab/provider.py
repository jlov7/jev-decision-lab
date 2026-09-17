"""Native TypeSafe transport. Replay is separate and never a live-error fallback."""
from __future__ import annotations
import json
import os
import threading
import time
import urllib.error
import urllib.request
from .engine import load, number

ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
PRICE_PER_MILLION_INPUT = .042  # Published 2026-09-17; an estimate, not an invoice.
MAX_INPUT_BYTES = 16000

class CallBudget:
    def __init__(self, limit: int = 20):
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1 <= limit <= 100:
            raise ValueError('Live call limit must be an integer from 1 to 100')
        self.limit, self.used, self.lock = limit, 0, threading.Lock()
    def reserve(self) -> None:
        with self.lock:
            if self.used >= self.limit:
                raise RuntimeError('Session API-attempt limit reached. No request was sent. Restart deliberately to reset; this is not an account billing limit.')
            self.used += 1

BUDGET = CallBudget(int(os.getenv('JEV_MAX_LIVE_CALLS','20')))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the bearer token to a redirected host.

def replay(case_id: str) -> dict:
    try: return load('replay')[case_id]
    except KeyError as exc: raise ValueError('No teaching fixture for this case') from exc

def live_enabled() -> bool:
    return os.getenv('JEV_ALLOW_LIVE') == '1' and bool(os.getenv('TYPESAFE_API_KEY'))

def live(payload: dict) -> tuple[dict,dict]:
    if not live_enabled():
        raise PermissionError('Live mode is disabled. Set JEV_ALLOW_LIVE=1 and TYPESAFE_API_KEY on the server; never paste a key into the UI.')
    body = json.dumps(payload,allow_nan=False).encode()
    if len(body) > MAX_INPUT_BYTES:
        raise ValueError('Request exceeds the lab 16,000-byte ceiling; it was not sent.')
    # No automatic retries: a timeout may already have been billed. Every attempt is explicit.
    BUDGET.reserve()
    request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
        'Authorization':'Bearer '+os.environ['TYPESAFE_API_KEY'], 'Content-Type':'application/json',
        'User-Agent':'jev-decision-lab/0.1'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    started = time.perf_counter()
    try:
        with opener.open(request,timeout=15) as response:
            raw = response.read(1_000_001)
            if len(raw)>1_000_000: raise ValueError('Response exceeds lab ceiling')
            result = json.loads(raw)
    except urllib.error.HTTPError as exc:
        messages={401:'API key rejected',403:'Account access denied',422:'Request/model contract rejected',429:'Rate limited; inspect Retry-After and retry explicitly',529:'Provider overloaded; retry explicitly after a delay'}
        raise RuntimeError(f'TypeSafe HTTP {exc.code}: {messages.get(exc.code,"request failed")}. No replay fallback was used.') from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('TypeSafe network request failed or timed out. Billing status may be unknown. No automatic retry or replay fallback was used.') from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError('TypeSafe returned invalid JSON. No replay fallback was used.') from None
    elapsed=(time.perf_counter()-started)*1000
    usage=result.get('usage',{}) if isinstance(result,dict) else {}
    tokens=usage.get('input_tokens')
    estimated=tokens/1_000_000*PRICE_PER_MILLION_INPUT if isinstance(tokens,int) and not isinstance(tokens,bool) and tokens>=0 else None
    return result, {'kind':'live_typesafe','model_calls':1,'latency_ms':round(elapsed,2),'usage':usage,
                    'estimated_cost_usd':estimated,'price_per_million_input_usd':PRICE_PER_MILLION_INPUT,
                    'price_as_of':'2026-09-17','warning':'Cost estimated from reported input usage and the dated published price. Latency includes client network time.'}
