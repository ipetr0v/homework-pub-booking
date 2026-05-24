"""Ex5 tools. Four tools the agent uses to research an Edinburgh booking.

Each tool:
  1. Reads its fixture from sample_data/ (DO NOT modify the fixtures).
  2. Logs its arguments and output into _TOOL_CALL_LOG (see integrity.py).
  3. Returns a ToolResult with success=True/False, output=dict, summary=str.

The grader checks for:
  * Correct parallel_safe flags (reads True, generate_flyer False).
  * Every tool's results appear in _TOOL_CALL_LOG.
  * Tools fail gracefully on missing fixtures or bad inputs (ToolError,
    not RuntimeError).
"""

from __future__ import annotations

from pathlib import Path

from sovereign_agent.session.directory import Session
from sovereign_agent.tools.registry import ToolRegistry, ToolResult, _RegisteredTool

_SAMPLE_DATA = Path(__file__).parent / "sample_data"


# ---------------------------------------------------------------------------
# TODO 1 — venue_search
# ---------------------------------------------------------------------------
def venue_search(near: str, party_size: int, budget_max_gbp: int = 1000) -> ToolResult:
    """Search for Edinburgh venues near <near> that can seat the party.

    Reads sample_data/venues.json. Filters by:
      * open_now == True
      * area contains <near> (case-insensitive substring match)
      * seats_available_evening >= party_size
      * hire_fee_gbp + min_spend_gbp <= budget_max_gbp

    Returns a ToolResult with:
      output: {"near": ..., "party_size": ..., "results": [<venue dicts>], "count": int}
      summary: "venue_search(<near>, party=<N>): <count> result(s)"

    MUST call record_tool_call(...) before returning so the integrity
    check can see what data was produced.
    """
    import json

    from sovereign_agent.errors import ToolError

    from starter.edinburgh_research.integrity import _TOOL_CALL_LOG, record_tool_call

    # Anti-spiral guard: stop after 3 searches
    search_count = sum(1 for r in _TOOL_CALL_LOG if r.tool_name == "venue_search")
    if search_count >= 3:
        return ToolResult(
            success=False,
            output={"error": "too_many_searches", "count": search_count},
            summary="STOP calling venue_search; use the results you already have.",
        )

    venues_path = _SAMPLE_DATA / "venues.json"
    if not venues_path.exists():
        return ToolResult(
            success=False,
            output={},
            summary="venues.json not found",
            error=ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message="sample_data/venues.json not found",
            ),
        )

    venues = json.loads(venues_path.read_text(encoding="utf-8"))
    near_lower = near.lower()

    results = [
        v
        for v in venues
        if v.get("open_now") is True
        and near_lower in v.get("area", "").lower()
        and v.get("seats_available_evening", 0) >= party_size
        and (v.get("hire_fee_gbp", 0) + v.get("min_spend_gbp", 0)) <= budget_max_gbp
    ]

    args = {"near": near, "party_size": party_size, "budget_max_gbp": budget_max_gbp}
    output = {"near": near, "party_size": party_size, "results": results, "count": len(results)}
    record_tool_call("venue_search", args, output)

    return ToolResult(
        success=True,
        output=output,
        summary=f"venue_search({near}, party={party_size}): {len(results)} result(s)",
    )


# ---------------------------------------------------------------------------
# TODO 2 — get_weather
# ---------------------------------------------------------------------------
def get_weather(city: str, date: str) -> ToolResult:
    """Look up the scripted weather for <city> on <date> (YYYY-MM-DD).

    Reads sample_data/weather.json. Returns:
      output: {"city": str, "date": str, "condition": str, "temperature_c": int, ...}
      summary: "get_weather(<city>, <date>): <condition>, <temp>C"

    If the city or date is not in the fixture, return success=False with
    a clear ToolError (SA_TOOL_INVALID_INPUT). Do NOT raise.

    MUST call record_tool_call(...) before returning.
    """
    import json

    from sovereign_agent.errors import ToolError

    from starter.edinburgh_research.integrity import record_tool_call

    weather_path = _SAMPLE_DATA / "weather.json"
    if not weather_path.exists():
        return ToolResult(
            success=False,
            output={},
            summary="weather.json not found",
            error=ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message="sample_data/weather.json not found",
            ),
        )

    data = json.loads(weather_path.read_text(encoding="utf-8"))
    city_lower = city.lower()
    args = {"city": city, "date": date}

    if city_lower not in data:
        record_tool_call("get_weather", args, {})
        return ToolResult(
            success=False,
            output={},
            summary=f"get_weather: city '{city}' not found",
            error=ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"City '{city}' not in weather data",
            ),
        )

    city_data = data[city_lower]
    if date not in city_data:
        record_tool_call("get_weather", args, {})
        return ToolResult(
            success=False,
            output={},
            summary=f"get_weather: date '{date}' not found for {city}",
            error=ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Date '{date}' not in weather data for {city}",
            ),
        )

    weather = city_data[date]
    output = {"city": city, "date": date, **weather}
    record_tool_call("get_weather", args, output)

    return ToolResult(
        success=True,
        output=output,
        summary=f"get_weather({city}, {date}): {weather['condition']}, {weather['temperature_c']}C",
    )


# ---------------------------------------------------------------------------
# TODO 3 — calculate_cost
# ---------------------------------------------------------------------------
def calculate_cost(
    venue_id: str,
    party_size: int,
    duration_hours: int,
    catering_tier: str = "bar_snacks",
) -> ToolResult:
    """Compute the total cost for a booking.

    Formula:
      base_per_head = base_rates_gbp_per_head[catering_tier]
      venue_mult    = venue_modifiers[venue_id]
      subtotal      = base_per_head * venue_mult * party_size * max(1, duration_hours)
      service       = subtotal * service_charge_percent / 100
      total         = subtotal + service + <venue's hire_fee_gbp + min_spend_gbp>
      deposit_rule  = per deposit_policy thresholds

    Returns:
      output: {
        "venue_id": str,
        "party_size": int,
        "duration_hours": int,
        "catering_tier": str,
        "subtotal_gbp": int,
        "service_gbp": int,
        "total_gbp": int,
        "deposit_required_gbp": int,
      }
      summary: "calculate_cost(<venue>, <party>): total £<N>, deposit £<M>"

    MUST call record_tool_call(...) before returning.
    """
    import json

    from sovereign_agent.errors import ToolError

    from starter.edinburgh_research.integrity import record_tool_call

    catering_path = _SAMPLE_DATA / "catering.json"
    venues_path = _SAMPLE_DATA / "venues.json"

    if not catering_path.exists() or not venues_path.exists():
        return ToolResult(
            success=False,
            output={},
            summary="fixture files not found",
            error=ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message="sample_data/catering.json or venues.json not found",
            ),
        )

    catering = json.loads(catering_path.read_text(encoding="utf-8"))
    venues = json.loads(venues_path.read_text(encoding="utf-8"))

    args = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
    }

    # Validate catering tier
    base_rates = catering["base_rates_gbp_per_head"]
    if catering_tier not in base_rates:
        record_tool_call("calculate_cost", args, {})
        return ToolResult(
            success=False,
            output={},
            summary=f"calculate_cost: unknown catering tier '{catering_tier}'",
            error=ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Unknown catering tier: {catering_tier}",
            ),
        )

    # Validate venue
    venue_modifiers = catering["venue_modifiers"]
    if venue_id not in venue_modifiers:
        record_tool_call("calculate_cost", args, {})
        return ToolResult(
            success=False,
            output={},
            summary=f"calculate_cost: unknown venue '{venue_id}'",
            error=ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Unknown venue: {venue_id}",
            ),
        )

    # Look up venue hire_fee and min_spend
    venue = next((v for v in venues if v["id"] == venue_id), None)
    hire_fee = venue["hire_fee_gbp"] if venue else 0
    min_spend = venue["min_spend_gbp"] if venue else 0

    # Calculate
    base_per_head = base_rates[catering_tier]
    venue_mult = venue_modifiers[venue_id]
    subtotal = base_per_head * venue_mult * party_size * max(1, duration_hours)
    service_pct = catering["service_charge_percent"]
    service = subtotal * service_pct / 100
    # min_spend is a floor, not an addition (office hours finding #2)
    effective_subtotal = max(subtotal, min_spend)
    total = effective_subtotal + service + hire_fee

    # Convert to int via round (consistent rounding per student discussion)
    subtotal_gbp = round(subtotal)
    service_gbp = round(service)
    total_gbp = round(total)

    # Deposit policy
    if total_gbp < 300:
        deposit = 0
    elif total_gbp <= 1000:
        deposit = int(total_gbp * 0.20)
    else:
        deposit = int(total_gbp * 0.30)

    output = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
        "subtotal_gbp": subtotal_gbp,
        "service_gbp": service_gbp,
        "total_gbp": total_gbp,
        "deposit_required_gbp": deposit,
    }
    record_tool_call("calculate_cost", args, output)

    return ToolResult(
        success=True,
        output=output,
        summary=f"calculate_cost({venue_id}, {party_size}): total £{total_gbp}, deposit £{deposit}",
    )


# ---------------------------------------------------------------------------
# TODO 4 — generate_flyer
# ---------------------------------------------------------------------------
def generate_flyer(session: Session, event_details: dict) -> ToolResult:
    """Produce an HTML flyer and write it to workspace/flyer.html.

    event_details is expected to contain at least:
      venue_name, venue_address, date, time, party_size, condition,
      temperature_c, total_gbp, deposit_required_gbp

    Write a self-contained HTML flyer (inline CSS, no external assets). Tag every key fact with data-testid="<n>" so the integrity check can parse it.

    Write a formatted HTML flyer with an H1 title, the event
    facts, a weather summary, and the cost breakdown.

    Returns:
      output: {"path": "workspace/flyer.html", "bytes_written": int}
      summary: "generate_flyer: wrote <path> (<N> chars)"

    MUST call record_tool_call(...) before returning — the integrity
    check compares the flyer's contents against earlier tool outputs.

    IMPORTANT: this tool MUST be registered with parallel_safe=False
    because it writes a file.
    """
    from starter.edinburgh_research.integrity import record_tool_call

    venue_name = event_details.get("venue_name", "TBC")
    venue_address = event_details.get("venue_address", "")
    date = event_details.get("date", "")
    time_ = event_details.get("time", "")
    party_size = event_details.get("party_size", "")
    condition = event_details.get("condition", "")
    temperature_c = event_details.get("temperature_c", "")
    total_gbp = event_details.get("total_gbp", "")
    deposit = event_details.get("deposit_required_gbp", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Event Flyer — {venue_name}</title>
  <style>
    body {{
      font-family: Georgia, 'Times New Roman', serif;
      max-width: 640px;
      margin: 2rem auto;
      padding: 1rem;
      background: #fafaf8;
      color: #333;
    }}
    h1 {{
      color: #2c3e50;
      border-bottom: 2px solid #e74c3c;
      padding-bottom: 0.5rem;
    }}
    dl {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 0.4rem 1rem;
    }}
    dt {{
      font-weight: bold;
      color: #555;
    }}
    dd {{
      margin: 0;
    }}
    .weather {{
      background: #eef6ff;
      border-left: 4px solid #3498db;
      padding: 0.8rem;
      margin: 1rem 0;
    }}
    .cost {{
      background: #fef9e7;
      border-left: 4px solid #f1c40f;
      padding: 0.8rem;
      margin: 1rem 0;
    }}
    footer {{
      margin-top: 2rem;
      font-size: 0.85rem;
      color: #999;
    }}
  </style>
</head>
<body>
  <article>
    <h1>🍺 {venue_name} — Event Booking</h1>
    <dl>
      <dt>Venue</dt>
      <dd data-testid="venue_name">{venue_name}</dd>
      <dt>Address</dt>
      <dd data-testid="venue_address">{venue_address}</dd>
      <dt>Date</dt>
      <dd data-testid="date">{date}</dd>
      <dt>Time</dt>
      <dd data-testid="time">{time_}</dd>
      <dt>Party Size</dt>
      <dd data-testid="party_size">{party_size}</dd>
    </dl>

    <div class="weather">
      <h2>Weather Forecast</h2>
      <dl>
        <dt>Condition</dt>
        <dd data-testid="condition">{condition}</dd>
        <dt>Temperature</dt>
        <dd data-testid="temperature">{temperature_c}°C</dd>
      </dl>
    </div>

    <div class="cost">
      <h2>Cost Breakdown</h2>
      <dl>
        <dt>Total</dt>
        <dd data-testid="total">£{total_gbp}</dd>
        <dt>Deposit Required</dt>
        <dd data-testid="deposit">£{deposit}</dd>
      </dl>
    </div>
  </article>
  <footer>Generated by Edinburgh Research Agent</footer>
</body>
</html>"""

    workspace = session.workspace_dir
    workspace.mkdir(parents=True, exist_ok=True)
    flyer_path = workspace / "flyer.html"
    flyer_path.write_text(html, encoding="utf-8")

    args = {"event_details": event_details}
    output = {"path": "workspace/flyer.html", "bytes_written": len(html.encode("utf-8"))}
    record_tool_call("generate_flyer", args, output)

    return ToolResult(
        success=True,
        output=output,
        summary=f"generate_flyer: wrote workspace/flyer.html ({len(html)} chars)",
    )


# ---------------------------------------------------------------------------
# Registry builder — DO NOT MODIFY the name, signature, or registration calls.
# The grader imports and calls this to pick up your tools.
# ---------------------------------------------------------------------------
def build_tool_registry(session: Session) -> ToolRegistry:
    """Build a session-scoped tool registry with all four Ex5 tools plus
    the sovereign-agent builtins (read_file, write_file, list_files,
    handoff_to_structured, complete_task).

    DO NOT change the tool names — the tests and grader call them by name.
    """
    from sovereign_agent.tools.builtin import make_builtin_registry

    reg = make_builtin_registry(session)

    # venue_search
    reg.register(
        _RegisteredTool(
            name="venue_search",
            description="Search Edinburgh venues by area, party size, and max budget.",
            fn=venue_search,
            parameters_schema={
                "type": "object",
                "properties": {
                    "near": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "budget_max_gbp": {"type": "integer", "default": 1000},
                },
                "required": ["near", "party_size"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
                    "output": {"count": 1, "results": [{"id": "haymarket_tap"}]},
                }
            ],
        )
    )

    # get_weather
    reg.register(
        _RegisteredTool(
            name="get_weather",
            description="Get scripted weather for a city on a YYYY-MM-DD date.",
            fn=get_weather,
            parameters_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city", "date"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"city": "Edinburgh", "date": "2026-04-25"},
                    "output": {"condition": "cloudy", "temperature_c": 12},
                }
            ],
        )
    )

    # calculate_cost
    reg.register(
        _RegisteredTool(
            name="calculate_cost",
            description="Compute total cost and deposit for a booking.",
            fn=calculate_cost,
            parameters_schema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "catering_tier": {
                        "type": "string",
                        "enum": ["drinks_only", "bar_snacks", "sit_down_meal", "three_course_meal"],
                        "default": "bar_snacks",
                    },
                },
                "required": ["venue_id", "party_size", "duration_hours"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # pure compute, no shared state
            examples=[
                {
                    "input": {
                        "venue_id": "haymarket_tap",
                        "party_size": 6,
                        "duration_hours": 3,
                    },
                    "output": {"total_gbp": 540, "deposit_required_gbp": 0},
                }
            ],
        )
    )

    # generate_flyer — parallel_safe=False because it writes a file
    def _flyer_adapter(event_details: dict) -> ToolResult:
        return generate_flyer(session, event_details)

    reg.register(
        _RegisteredTool(
            name="generate_flyer",
            description="Write an HTML flyer for the event to workspace/flyer.html.",
            fn=_flyer_adapter,
            parameters_schema={
                "type": "object",
                "properties": {"event_details": {"type": "object"}},
                "required": ["event_details"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=False,  # writes a file — MUST be False
            examples=[
                {
                    "input": {
                        "event_details": {
                            "venue_name": "Haymarket Tap",
                            "date": "2026-04-25",
                            "party_size": 6,
                        }
                    },
                    "output": {"path": "workspace/flyer.html"},
                }
            ],
        )
    )

    return reg


__all__ = [
    "build_tool_registry",
    "venue_search",
    "get_weather",
    "calculate_cost",
    "generate_flyer",
]
