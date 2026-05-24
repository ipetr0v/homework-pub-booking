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

In early real-mode runs (`sess_7dc15a1150a7`), Qwen3-32B ignored
the task prompt and called `venue_search` four times with fabricated
params: party sizes of 10, 20, 15, 50 across areas like "Edinburgh
City Centre" and "Grassmarket". All returned zero results, and the
agent spiraled without producing a flyer.

If it HAD reached `generate_flyer` with made-up costs,
`verify_dataflow` would catch it: it pulls every £-amount and
temperature from the HTML and checks if any tool actually produced
that number. It checks provenance in `_TOOL_CALL_LOG`, not
plausibility — so even a reasonable-looking "£540" fails if
`calculate_cost` never returned it.

After fixing the spiral (anti-spiral guard + runtime overrides for
cross-subgoal data injection), the successful run
`sess_9fd4544aad92` verified 5 facts against tool outputs: venue
name, address, weather condition, temperature, and total cost. All
traced back to actual tool calls. This confirmed the integrity
check works end-to-end: it's not just catching fabrication in
theory — it's the reason we can trust the flyer in the successful
run. Without `verify_dataflow`, we'd have no way to distinguish
the correct flyer from one with plausible but wrong numbers.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/trace.jsonl` lines 3–8: the four fabricated venue_search calls
- `sessions/examples/ex5-edinburgh-research/sess_9fd4544aad92/logs/trace.jsonl`: successful run, 5 facts verified
- `starter/edinburgh_research/integrity.py` — `verify_dataflow` with per-tool fact verification

---

## Q3 — First production failure

### Your answer

If I were shipping this agent to a real pub-booking business next week,
the first production failure I'd expect is the LLM calling `venue_search`
with hallucinated parameters. I saw this firsthand: in
`sess_7dc15a1150a7`, Qwen3-32B searched for "Edinburgh City Centre"
with party_size=50 instead of "Haymarket" with party_size=6. Every
call returned zero results and the customer got nothing.

The sovereign-agent primitive that would surface this failure is the
**ticket state machine**. In the spiral session, ticket `tk_62bfc85f`
shows `tool_calls: 6` and `handoff_requested: true` — the executor
made 6 calls with zero useful results. In production, you'd monitor
ticket state transitions: if tool-call count exceeds 2× the planner's
estimate with zero successes, force-fail the ticket with a diagnostic.

I fixed this with three layers: (1) an anti-spiral guard capping
`venue_search` at 3 calls, (2) patching the executor loop to inject sg_1's tool
outputs into sg_2's description (solving cross-subgoal data loss),
and (3) prescriptive system prompts with exact tool-call sequences.
The fix worked: `sess_9fd4544aad92` ran end-to-end with Qwen calling
all four tools correctly and producing a verified flyer.

But these are application-level mitigations. The ticket state machine
is the framework-level primitive that should catch this failure
generically — it already tracks `estimated_tool_calls` vs actual calls.
You just need to enforce the invariant rather than letting the executor
run indefinitely.

### Citation

- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/tickets/tk_62bfc85f/manifest.json`: `tool_calls: 6`, `handoff_requested: true`
- `sessions/examples/ex5-edinburgh-research/sess_9fd4544aad92/logs/trace.jsonl`: successful run after fixes
- `starter/edinburgh_research/run.py` lines 43–310: runtime patches for executor loop and subgoal data passing
