# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

In my Ex7 run (`sess_8ebb579c26f9`), the bridge ran two rounds. In
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
confirmed the booking.

What's interesting is that the planner always assigns `"loop"` to the
subgoal — it doesn't assign `"structured"` directly. The handoff to
structured happens at the executor level via the `handoff_to_structured`
tool call. So the planner's role is to decide WHAT to do (find a venue),
while the executor decides WHEN to hand off (after research is done).
The structured half never gets "planned into" — it gets "called into"
by the loop when the loop decides it has enough data for a booking.

### Citation

- `sessions/examples/ex7-handoff-bridge/sess_8ebb579c26f9/logs/trace.jsonl`: round 1 and round 2 traces
- `starter/handoff_bridge/run.py` lines 30–53: planner subgoals for rounds 1 and 2 (`assigned_half: "loop"`)
- `starter/handoff_bridge/run.py` lines 69–87: executor's `handoff_to_structured` call with reason "under policy rules"

---

## Q2 — Dataflow integrity catch

### Your answer

I ran `make ex5-real` twice and Qwen spiraled both times — it never
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
tried".

Now imagine if it HAD gotten to `generate_flyer` and just made up some
costs. That's exactly what `verify_dataflow` catches: it pulls every
£-amount and temperature from the HTML and checks if any tool actually
produced that number. It doesn't care if the number looks reasonable —
it checks if the number has provenance in `_TOOL_CALL_LOG`. So even
a plausible "£540" would fail if `calculate_cost` was never called.

The office hours highlighted a deeper problem: the original integrity
check was self-verifying. When `generate_flyer` writes `total_gbp=540`
into `_TOOL_CALL_LOG` via `record_tool_call`, and then `verify_dataflow`
scans that same log, it finds 540 in the flyer tool's own arguments.
The fact verifies its own existence. The fix: verify against specific
tool outputs — venue facts must come from `venue_search`, cost facts
from `calculate_cost`, weather facts from `get_weather`. Never from
`generate_flyer`'s own entry.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/trace.jsonl` lines 3–8: the four fabricated venue_search calls
- `sessions/examples/ex5-edinburgh-research/sess_474c8686d84a/logs/trace.jsonl` line 3: first run, same spiral pattern
- `starter/edinburgh_research/integrity.py` — `verify_dataflow` with per-tool fact verification

---

## Q3 — First production failure

### Your answer

If I were shipping this agent to a real pub-booking business next week,
the first production failure I'd expect is the LLM calling `venue_search`
with hallucinated parameters — areas and party sizes it invented rather
than what the customer specified. I saw this firsthand: in
`sess_7dc15a1150a7` and `sess_474c8686d84a`, Qwen3-32B ignored the
task prompt entirely and searched for "Edinburgh City Centre" with
party_size=50 instead of "Haymarket" with party_size=6. Every call
returned zero results, the agent spiraled, and the customer got nothing.

The sovereign-agent primitive that would surface this failure is the
**ticket state machine**. Each executor subgoal runs inside a ticket
(`tk_62bfc85f` in the spiral session, for example). A ticket transitions
through states: `pending → running → success/failed`. In that spiral
run, the ticket's manifest shows `tool_calls: 6` and
`handoff_requested: true` — the executor made 6 tool calls with zero
useful results before giving up.

In production, you'd wire a monitor on ticket state transitions: if a
ticket's tool-call count exceeds 2× the planner's estimate with zero
successful results, the ticket should be force-failed with a diagnostic
explaining what the LLM did wrong. This is exactly the "executor
improvises when given an under-specified task" failure from the office
hours slides (Finding 5). The ticket state machine gives you the
hook — it already tracks `estimated_tool_calls` vs actual calls in
the ticket result. You just need to enforce the invariant rather than
letting the executor run indefinitely.

The anti-spiral guard I added to `venue_search` (cap at 3 calls) is
a tool-level mitigation, but the ticket state machine is the
framework-level primitive that should catch this category of failure
generically across all tools.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/trace.jsonl`: 4 fabricated venue_search calls with zero successes
- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/tickets/tk_62bfc85f/manifest.json`: executor ticket showing `tool_calls: 6`, `handoff_requested: true` — spiral evidence
- `starter/edinburgh_research/tools.py` lines 50–57: anti-spiral guard as tool-level mitigation
