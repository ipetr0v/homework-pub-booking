# Ex6 — Rasa structured half

## Your answer

The RasaStructuredHalf POSTs booking data to Rasa's REST webhook and
parses the response. The flow is: loop half produces raw booking
data, `normalise_booking_payload` in `validator.py` converts it to
Rasa's expected message shape with canonical types (venue_id as slug,
party_size as int, deposit as parsed GBP amount), then the structured
half POSTs to Rasa and looks for `{action: committed}` or
`{action: rejected}` in the custom payload.

I ran both offline and real modes. The offline mock (`make ex6`)
uses a stdlib `http.server` thread that always confirms — useful
for unit tests. The real Rasa run (`make ex6-real`, session
`sess_7b7e2242d366`) hit the actual Rasa Pro CALM engine on port
5005, with the custom action server on port 5055. Both confirmed
the booking (booking reference visible in console output).

The validators in `validator.py` handle normalisation before the
POST: `parse_currency_gbp` handles multiple formats ("£200", "200",
"200.00"), `canonicalise_venue_id` slugifies venue names
("Haymarket Tap" → "haymarket_tap"), and `parse_party_size` rejects
zero or negative values. These run before the POST, so Rasa never
sees malformed data.

## Citations

- `starter/rasa_half/structured_half.py` — `RasaStructuredHalf.run` and mock server
- `starter/rasa_half/validator.py` — `normalise_booking_payload` and parse helpers
- `sessions/examples/ex6-rasa-half/sess_7b7e2242d366/session.json` — real Rasa run metadata
