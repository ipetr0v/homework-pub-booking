# Ex7 — Handoff bridge

## Your answer

The HandoffBridge orchestrates round-trips between the loop and
structured halves. In my offline run (`sess_8ebb579c26f9`), the
bridge ran two rounds:

Round 1: the loop half searched for a venue near Haymarket for a
party of 12, found haymarket_tap (8 seats), and called
`handoff_to_structured` with reason "passing to structured half
for confirmation under policy rules". The structured half rejected
it because party_size=12 exceeds haymarket_tap's 8-seat capacity.

Round 2: the bridge built a reverse task containing the rejection
reason and passed it back to the loop half. The loop retried with
a different search ("Old Town", party_size=6), found royal_oak
(16 seats), and handed off again. This time the structured half
confirmed the booking (reference generated dynamically by mock Rasa).

The reverse-task mechanism is the interesting part. On rejection,
the bridge rewrites the task to include `prior_result`,
`rejection_reason`, and `retry=True`. The loop half sees this in
its next invocation and picks a scripted alternative (in offline
mode). In real LLM mode, the executor would read the rejection
reason and adjust its search accordingly.

The bridge caps at `max_rounds=3` to prevent infinite loops. Each
transition emits trace events so the integrity check can verify
that at least one round_start and one state_changed event occurred.

## Citations

- `sessions/examples/ex7-handoff-bridge/sess_8ebb579c26f9/logs/trace.jsonl` — 2-round bridge trace
- `starter/handoff_bridge/bridge.py` — `HandoffBridge.run` and reverse task builder
- `starter/handoff_bridge/run.py` lines 56–121 — scripted two-round trajectory
