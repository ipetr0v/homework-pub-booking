# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

In my Ex7 run (`sess_61285be6f7d5`), the bridge ran two rounds. In
round 1 the planner produced a single subgoal with `assigned_half:
"loop"` — "find venue near haymarket for 12". The loop half searched
for venues, found haymarket_tap, then called `handoff_to_structured`
with reason: "loop half identified a candidate venue; passing to
structured half for confirmation under policy rules".

The key phrase is "under policy rules". The executor doesn't decide
this arbitrarily — the task description says "book a venue", and the
tool registry includes `handoff_to_structured`. When the loop half
finishes its research (finding a venue, checking availability), the
natural next step is validation against booking constraints. That's
what the structured half is for: deterministic rules that shouldn't
be left to LLM judgment.

The structured half then rejected the booking — party of 12 exceeds
haymarket_tap's 8-seat cap. The bridge caught the rejection and
kicked the loop half back in for round 2 with a new plan: "retry
with larger venue after rejection". This time the loop found
royal_oak (16 seats), handed off again, and the structured half
confirmed with ref `BK-7D401E9E`.

What's interesting is that the planner always assigns `"loop"` to the
subgoal — it doesn't assign `"structured"` directly. The handoff to
structured happens at the executor level via the `handoff_to_structured`
tool call. So the planner's role is to decide WHAT to do (find a venue),
while the executor decides WHEN to hand off (after research is done).
The structured half never gets "planned into" — it gets "called into"
by the loop when the loop decides it has enough data for a booking.

### Citation

- `starter/handoff_bridge/run.py` lines 30–53: planner subgoals for rounds 1 and 2 (`assigned_half: "loop"`)
- `starter/handoff_bridge/run.py` lines 69–87: executor's `handoff_to_structured` call with reason "under policy rules"
- Ex7 offline output: "Bridge outcome: completed, rounds: 2, summary: structured confirmed in round 2"

---

## Q2 — Dataflow integrity catch

### Your answer

I ran `make ex5-real` twice and Qwen spiraled both times, it never
even got to the flyer. But the trace logs are more interesting
than a clean run would've been.

The task prompt spells out
`venue_search(near='Haymarket', party_size=6, budget_max_gbp=800)`.
Qwen ignored all of that. In `sess_7dc15a1150a7` it called
`venue_search` four times with completely made-up params:

```json
{"tool": "venue_search", "arguments": {"near": "Edinburgh City Centre", "party_size": 10}, "summary": "venue_search(Edinburgh City Centre, party=10): 0 result(s)"}
{"tool": "venue_search", "arguments": {"near": "Old Town", "party_size": 20}, "summary": "venue_search(Old Town, party=20): 0 result(s)"}
{"tool": "venue_search", "arguments": {"near": "Grassmarket", "party_size": 15}, "summary": "venue_search(Grassmarket, party=15): 0 result(s)"}
{"tool": "venue_search", "arguments": {"near": "Edinburgh", "party_size": 50, "budget_max_gbp": 500}, "summary": "venue_search(Edinburgh, party=50): 0 result(s)"}
```

Party sizes of 10, 20, 15, 50: none of these are 6. All returned
zero results because the fixture only has a Haymarket match for small
parties. After four misses it gave up and handed off to structured
with "Venue search tools are not returning results for any parameters
tried". It was searching for the wrong thing.

Now imagine if it HAD gotten to `generate_flyer` and just made up some
costs. That's exactly what `verify_dataflow` catches: it pulls every
£-amount and temperature from the HTML and checks if any tool actually
produced that number. It doesn't care if the number looks reasonable,
it checks if the number has provenance in `_TOOL_CALL_LOG`. So even
a plausible "£540" would fail if `calculate_cost` was never called.

The big takeaway for me: don't validate outputs by asking "does this
look right?": validate by asking "did a tool actually say this?"
That's the whole point of `record_tool_call`.

### Citation

- `sess_7dc15a1150a7/logs/trace.jsonl` lines 3–8: the four fabricated venue_search calls
- `sess_7dc15a1150a7/ipc/handoff_to_structured.json`: handoff with all failed attempts listed
- `sess_474c8686d84a/logs/trace.jsonl` line 3: first run, same pattern: `near='Old Town', party_size=50`

---

## Q3 — Removing one framework primitive

### Your answer

If I had to remove one framework primitive and keep the rest, I'd
drop tickets (the planner's subgoal tracking mechanism) and keep
session directories.

Session directories are the foundation everything else sits on.
Looking at my actual runs, each session (`sess_7dc15a1150a7`,
`sess_7b7e2242d366`, `sess_a8ca30e9ff53`) is a self-contained
directory with `session.json`, `logs/trace.jsonl`, `ipc/`, and
`workspace/`. When I needed to debug why Qwen spiraled, I just
did `cat trace.jsonl` and saw every tool call with timestamps.
When the Ex7 bridge rejected a booking, the reason was sitting
in `ipc/handoff_to_structured.json`. No database, no log
aggregation, just files.

Without session directories, debugging becomes painful. The
trace events would have to go somewhere (a database? stdout?),
handoff state would need shared memory or a message queue, and
you'd lose the ability to `ls` a session to see what happened.
Every other primitive can be rebuilt on top of directories:
tickets become `.jsonl` files, IPC becomes file drops, the
state machine becomes a `state` field in `session.json`.

Tickets, on the other hand, are convenient but not load-bearing.
The planner produces subgoals and the executor runs them, but
you could track that with a simple list in the session file.
The offline Ex7 run doesn't even use real ticket tracking —
the scripted responses hardcode the subgoal sequence.

### Citation

- `sess_7dc15a1150a7/` — session directory structure I used for debugging Ex5 spirals
- `sess_7b7e2242d366/session.json` — Ex6 session metadata showing the directory layout
- `sess_a8ca30e9ff53/logs/trace.jsonl` — Ex8 trace file, accessible via plain `cat`

