# Start here

Someone sent you this repository. Here is what it is and what to do in the first ten minutes.

## What it is

A small app that runs on your own computer and shows you what TypeSafe's Jev model does with a business situation. Jev does not write text back. It answers typed questions with probabilities: which team should look at this, how severe is it, is the evidence enough, yes or no. The app puts those answers next to the rules your organisation would apply, so you can see what the model contributes and what your own code still has to decide.

It uses twelve made-up cases from three industries. Nothing in it is real company data, and it asks you to keep it that way.

## Ten minutes, no key

You need Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jlov7/jev-decision-lab.git
cd jev-decision-lab
uv run jev-lab
```

Open http://127.0.0.1:8765. You are in replay mode: the numbers are authored teaching fixtures, and a banner at the top says so.

1. On the Workbench, case S02 is already selected: "The word delay is not a delay". Click **Run six judgments**. Open *Investigating team* to see the probabilities.
2. Change *Source metadata simulation* to **Evidence has expired** and click **Replay policy**. The route changes with zero new model calls. Code applied a new constraint to an old judgment.
3. Pick S04, "Confident, but the wrong team", and run it. The authored fixture is 98% sure of the wrong answer. That is deliberate. Confidence is not correctness, and the app is built to keep reminding you.

## An hour, with a key

1. Get an API key from [console.typesafe.ai](https://console.typesafe.ai) under Settings → API keys.
2. Click **Connect Jev** at the top right of the app, paste the key, click **Connect**. It stays in the app's own server process on your machine and nowhere else. Click **Forget this key** when you are done, or just stop the server.
3. Open **Live lab**, tick the consent box, click **Fire 12 cases**. About a second later you have twelve real answers, their latency and their cost. Expect a fraction of a cent.
4. Scroll to **Experiments**. Probe one case eight times and watch how far the probabilities move. Then remove the evidence one excerpt at a time and see which excerpt the judgment was leaning on.

Each server process caps live attempts at 20 by default. A burst uses 12. If you want a longer session, start the server with a higher cap:

```bash
JEV_MAX_LIVE_CALLS=100 uv run jev-lab
```

## What to keep in mind

- Twelve cases are a smoke test, not a benchmark. The app says this everywhere numbers appear.
- The model recommends; the code decides; a person approves. The app never performs a real action.
- Never paste real work data into the playground. The cases are synthetic on purpose.
- If a key ever appears in a log, a screenshot or a message, rotate it.

The full guide is the [README](../README.md). The workshop script for running this with a group is [WORKSHOP.md](WORKSHOP.md).
