# Access, first call and troubleshooting

## Start without an account

From the repository root:

```bash
uv run python3 scripts/setup_lab.py
uv run python3 -m unittest discover -s tests -v
uv run python3 -m jev_lab check
uv run python3 -m jev_lab
```

Open `http://127.0.0.1:8765`. No package installation or API key is needed for the teaching application. The server binds only to the loopback interface. Stop with Control-C. Use `--port 8766` after `serve` when the default port is occupied.

## What your TypeSafe account enables

The official quick start describes a console Playground and dashboard API keys. Open `https://console.typesafe.ai`, verify that Playground and key creation are enabled, and inspect your own credits and access. This research did not log into your account, read your plan or verify an entitlement. Joining the waitlist, receiving an account and having working API access are distinct states. [S02]

In Playground, use a clearly synthetic sentence and three questions: one category, one ordered score, and one yes/no proposition. Read the returned distributions before designing an automation. Put all meaning in instructions and criteria; do not rely on the question ID carrying semantics.

## Connect the local lab

In the same terminal that will run the server:

```bash
read -s TYPESAFE_API_KEY
export TYPESAFE_API_KEY
export JEV_ALLOW_LIVE=1
export JEV_MODEL=jev-1.13.0
uv run python3 -m jev_lab
```

The first command waits for the key without echoing it. This avoids placing the literal key in shell history. The program does not automatically read a `.env` file. Do not paste the key into the browser or a coding-agent conversation. Restart an already-running server after changing environment variables.

Choose Live TypeSafe API, check the explicit consent box and run one bundled case. A server-side key alone does not cause an automatic call. For a terminal smoke test:

```bash
uv run python3 -m jev_lab smoke --mode live --allow-network --out runs/first-live.json
```

This sends one synthetic case. It does not verify your organization’s approval, calibrate the model, establish cost at scale or exercise a competitor.

After the session, remove variables and stop the server:

```bash
unset TYPESAFE_API_KEY JEV_ALLOW_LIVE
```

Rotate a key immediately if it has appeared in logs, screenshots, prompts or source control. Deleting a leaked key from a later commit does not remove it from history.

## Live lab and the Claude baseline

With the key configured, the **Live lab** tab fires all twelve cases concurrently and reports p50/p95 client latency, tokens and an estimated cost per run; the **playground** sends text you type with questions you declare; **compare** runs Jev beside a constrained-output Claude baseline on the same cases. Each burst or compare uses twelve attempts against the per-process caps (`JEV_MAX_LIVE_CALLS`, default 20; `JEV_MAX_COMPARE_CALLS`, default 40); raise them deliberately if you want several runs in one session.

The Claude arm needs the optional SDK and its own key in the same terminal:

```bash
uv sync --extra compare
read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
export JEV_COMPARE_MODEL=claude-haiku-4-5   # or claude-sonnet-5 / claude-opus-5
uv run python3 -m jev_lab
```

It returns categories only, so its distribution track is reported unavailable; agreement with the twelve teaching labels is a smoke test, not accuracy.

## Minimal native request

The SDK is not required by the lab, but the official Python package is `typesafe-sdk` and the JavaScript package is `@typesafe-ai/sdk`. The native endpoint is `POST https://api.typesafe.ai/v1/systemone`, authenticated with a bearer token. Use the official reference for current supported fields. [S02, S03]

Save this authored example as `example-request.json`:

```json
{
  "model": "jev-1.13.0",
  "state": {
    "message": "Please close the delay alert; receiving confirmed the delivery arrived on time.",
    "source": "synthetic learning example"
  },
  "questions": {
    "investigating_team": {
      "type": "choice",
      "instructions": "Which listed team should inspect this update? Use only the supplied state.",
      "criteria": {
        "operations": "Delivery planning and logistics",
        "quality": "Material specification or product integrity",
        "other": "No listed team is a defensible match"
      }
    }
  }
}
```

Then, with the environment key already configured:

```bash
curl --fail-with-body --max-time 15 \
  https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @example-request.json
```

Do not assume this example’s output in advance. Save the actual result with its model and usage fields. Your application, not the output category, must own the final policy decision.

## Alternate route: Vercel AI Gateway

Vercel’s September 16 release describes AI SDK 7.0.105+ and `experimental_evaluate` with model `typesafe-ai/jev`. The Gateway schema calls the yes/no primitive `boolean`; the native schema uses `noul`. TypeSafe’s separate confidence metadata is exposed through provider metadata. This route is not implemented or live-tested by the current Python adapter. [S11]

Use Gateway account credentials and its actual evaluation-model documentation, rather than sending a TypeSafe key to the wrong endpoint. Do not assume a native model ID, response parser or retention setting carries across routes unchanged. Existing Gateway approval also does not automatically cover a newly available underlying provider.

## Failure guide

| Symptom | Likely cause or question | Response |
|---|---|---|
| `No module named jev_lab` | Wrong working directory or source not unpacked | Run from repository root; inspect `jev_lab/__main__.py` |
| Live mode not configured | Key/enable flag missing from this process | Configure terminal environment and restart; .env is not auto-loaded |
| 401 | Invalid/revoked key | Check dashboard and rotate if necessary; never print the key |
| 403 | Account/model access or permission | Confirm entitlement with the provider; do not retry repeatedly |
| 422 | Payload/model contract rejected | Inspect request against current official schema; do not invent fields |
| 429 | Rate limit | Respect actual Retry-After; retry deliberately after checking budget |
| 529 or service error | Provider overload/unavailability | Retain the failure, pause; no synthetic fallback |
| Timeout | Network or provider uncertainty | Treat billing status as unknown; no automatic repeat |
| Pinned identity mismatch | Model alias/contract changed | Stop and inspect returned identity before reusing thresholds |
| Missing Score probabilities | Actual response differs from required contract | Preserve a redacted raw response; resolve the mismatch rather than fabricate a distribution |
| Receipt expired | Server restarted or 200-entry cap passed | Rerun the synthetic case; exported receipts remain separate artifacts |
| Nothing changes after adjusting slider | Slider changes configuration only | Click Replay policy; this deliberately separates editing from execution |
| Old result still visible after live error | Previous receipt retained | Read the error banner; it explicitly says no new result was produced |
| Browser connection blocked | Device policy or wrong host/port | Use approved local tooling; do not disable organizational controls |
| Corporate network needs a proxy | Lab transport intentionally avoids environment proxies | Have the approved platform adapter implement the required route; do not bypass IT |

## Enterprise intake checklist

Before any real work data, identify the specific workflow owner, data classifications, usage rights, provider/route approval, applicable API agreement, DPA, input/output retention, subprocessors, region, logging, deletion and incident procedures. Obtain relevant security evidence instead of assuming it is absent or present. Confirm budget controls, keys, model-version changes, failure SLAs and a review route.

The native privacy policy’s no-training statement is not a no-retention statement. Website Site terms are not a complete API-commercial contract. Gateway privacy controls are route-specific and do not settle all organizational obligations. [S12, S13, S11]

The personal-device lab is only a synthetic/public learning environment. It is not a permission to transfer internal material or bypass employment, intellectual-property, confidentiality or security rules.
