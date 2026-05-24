# Ex5 — Edinburgh research loop scenario

## Your answer

I implemented four tools in `starter/edinburgh_research/tools.py`:
`venue_search`, `get_weather`, `calculate_cost`, and `generate_flyer`.
Each reads from JSON fixtures in `sample_data/`, calls
`record_tool_call()` to log arguments and outputs, and returns a
`ToolResult`.

In the offline run (`make ex5`, session `sess_da1fd5c8b1f6`), the
planner produced two subgoals: sg_1 "research Edinburgh venues near
Haymarket for a party of 6" and sg_2 "produce an HTML flyer with
the chosen venue, weather, and cost". The executor ran sg_1 by
calling `venue_search`, `get_weather`, and `calculate_cost` in
parallel (all three are `parallel_safe=True` because they only read
fixtures). Then sg_2 called `generate_flyer` (`parallel_safe=False`
because it writes `workspace/flyer.html`). The dataflow integrity
check verified 5 facts against tool outputs.

I also fixed two bugs flagged during office hours: the cost formula
was adding `min_spend_gbp` instead of treating it as a floor
(`max(subtotal, min_spend)`), and there was no anti-spiral guard.
I added a search counter that stops `venue_search` after 3 calls
with a "STOP calling venue_search" message.

The real LLM runs were more interesting. In `sess_7dc15a1150a7`
(Qwen3-32B), the executor ignored the task prompt. The task said
`venue_search(near='Haymarket', party_size=6)` but Qwen called it
four times with fabricated params: party sizes of 10, 20, 15, and
50 across areas like "Edinburgh City Centre" and "Grassmarket".
All returned 0 results and it handed off to structured with
"Venue search tools are not returning results."

## Citations

- `sessions/examples/ex5-edinburgh-research/sess_da1fd5c8b1f6/logs/trace.jsonl` — offline run trace
- `sessions/examples/ex5-edinburgh-research/sess_da1fd5c8b1f6/workspace/flyer.html` — generated flyer
- `sessions/examples/ex5-edinburgh-research/sess_7dc15a1150a7/logs/trace.jsonl` — real LLM spiral
- `starter/edinburgh_research/tools.py` — tool implementations with anti-spiral guard
- `starter/edinburgh_research/integrity.py` — `verify_dataflow` and `record_tool_call`
