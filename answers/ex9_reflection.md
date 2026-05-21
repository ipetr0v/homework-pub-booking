# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

In my Ex7 run (session sess_a382a2149fc1), the planner's second
subgoal was sg_2 "commit the booking under policy rules" with
assigned_half: "structured". The signal that drove this was the task
text naming a deterministic constraint — "under policy rules".
Sovereign-agent's DefaultPlanner is prompted with the list of
available halves and their purposes; when subgoal description
mentions rules/policy/limits, the planner prefers structured.

This decision is advisory, not physical. The orchestrator respects
it only because both halves are wired up. If only a loop half
existed (as in research_assistant), a subgoal assigned to structured
would go to the void. That's failure mode #4 from the course slides.

The broader lesson: the planner makes an architectural decision
based on prose interpretation. Put the rules somewhere the LLM
cannot mis-assign — in the structured half's Python — and prose
ambiguity no longer matters.

### Citation

- sessions/sess_a382a2149fc1/logs/tickets/tk_*/raw_output.json
- sessions/sess_a382a2149fc1/logs/trace.jsonl:23

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

I'd keep session directories (Decision 1) as the last thing standing
and rebuild everything else if forced. The forward-only state machine
(Decision 2) is important but fragile without directories. Tickets
(Decision 3) I could rebuild as .jsonl files inside the session.
Atomic-rename IPC (Decision 5) is replaceable by directory polling.

Session directories are the irreplaceable piece. Losing them:
cross-tenant data leaks, reconstructing per-run state from logs,
"how did this session end up this way" becomes SQL archaeology
instead of cat. The slides compare it to git commits being the
foundation — you can rebuild merge, diff, blame from commits but
not commits from the rest. Session directories are commits.

### Citation

- sessions/sess_de44a1b8eb12/ — the directory itself
- sessions/sess_a382a2149fc1/logs/trace.jsonl
