# Ex5 — Edinburgh research loop scenario

## Your answer

I implemented four tools in `starter/edinburgh_research/tools.py`:
`venue_search`, `get_weather`, `calculate_cost`, and `generate_flyer`.
Each reads from JSON fixtures in `sample_data/`, calls
`record_tool_call()` to log arguments and outputs, and returns a
`ToolResult`.

In the offline run (`make ex5`, session `sess_70a6cf5bad08`), the
planner produced two subgoals: sg_1 "research Edinburgh venues near
Haymarket for a party of 6" and sg_2 "produce an HTML flyer with
the chosen venue, weather, and cost". The executor ran sg_1 by
calling `venue_search`, `get_weather`, and `calculate_cost` in
parallel (all three are `parallel_safe=True` because they only read
fixtures). Then sg_2 called `generate_flyer` (`parallel_safe=False`
because it writes `workspace/flyer.html`). The dataflow integrity
check verified 5 facts against tool outputs.

The real LLM runs were more interesting. In `sess_7dc15a1150a7`
(Qwen3-32B), the executor ignored the task prompt entirely. The
task said `venue_search(near='Haymarket', party_size=6)` but Qwen
called it four times with fabricated params: party sizes of 10, 20,
15, and 50 across areas like "Edinburgh City Centre" and
"Grassmarket". All returned 0 results and it gave up, handing off
to structured with "Venue search tools are not returning results
for any parameters tried."

The key design decision was making `venue_search` filter by area
as a case-insensitive substring match. This means "Haymarket"
matches the fixture but "Edinburgh City Centre" doesn't, which
is what exposed the LLM spiral. The integrity system
(`record_tool_call` + `verify_dataflow`) ensures that any facts in
the flyer must trace back to actual tool outputs, not LLM
fabrication.

## Citations

- `starter/edinburgh_research/tools.py` — the four tool implementations
- `starter/edinburgh_research/integrity.py` — `verify_dataflow` and `record_tool_call`
- `sess_7dc15a1150a7/logs/trace.jsonl` — real LLM run showing fabricated parameters
- `sess_474c8686d84a/logs/trace.jsonl` — first real run, same spiral pattern
