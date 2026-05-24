# Ex5 — Edinburgh research loop scenario

## Your answer

I implemented four tools in `starter/edinburgh_research/tools.py`:
`venue_search`, `get_weather`, `calculate_cost`, and `generate_flyer`.
Each reads from JSON fixtures in `sample_data/`, calls
`record_tool_call()` to log arguments and outputs, and returns a
`ToolResult`.

I fixed two bugs flagged during office hours: the cost formula was
adding `min_spend_gbp` instead of treating it as a floor
(`max(subtotal, min_spend)`), and there was no anti-spiral guard.
I added a search counter that stops `venue_search` after 3 calls.

In the offline run (`make ex5`, session `sess_da1fd5c8b1f6`), the
planner produced two subgoals and the executor ran all four tools.
The dataflow integrity check verified 5 facts against tool outputs.

Early real LLM runs spiraled badly. In `sess_7dc15a1150a7`
(Qwen3-32B), the executor called `venue_search` four times with
fabricated params (party sizes 10, 20, 15, 50 across wrong areas)
and got zero results every time.

The fix required two runtime patches in `run.py`: (1) overriding
`_react_loop` to block `complete_task` until `generate_flyer` has
run, preventing premature completion; (2) patching `LoopHalf.run`
to inject sg_1's tool outputs (venue name, weather, cost) into
sg_2's description as literal values, solving the cross-subgoal
data loss problem. Combined with prescriptive system prompts and
the anti-spiral guard, `sess_9fd4544aad92` ran end-to-end: Qwen
called all four tools with correct parameters and produced a
verified flyer with 5 matching facts.

## Citations

- `sessions/examples/ex5-edinburgh-research/sess_da1fd5c8b1f6/logs/trace.jsonl` — offline run trace
- `sessions/examples/ex5-edinburgh-research/sess_9fd4544aad92/logs/trace.jsonl` — successful real LLM run
- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/trace.jsonl` — real LLM spiral (pre-fix)
- `starter/edinburgh_research/tools.py` — tool implementations with anti-spiral guard
- `starter/edinburgh_research/run.py` lines 43–310 — runtime patches for executor loop and subgoal data passing
