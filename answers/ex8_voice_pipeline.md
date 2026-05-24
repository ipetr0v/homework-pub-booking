# Ex8 — Voice pipeline

## Your answer

The voice pipeline has two modes sharing the same trace event contract.
I ran text mode (`make ex8-text`, session `sess_e8cff95ecff4`) which
reads from stdin and gets replies from the ManagerPersona backed by
Llama-3.3-70B. Voice mode would use Speechmatics STT + TTS but
degrades to text mode when the API keys aren't set.

In my session I had a 4-turn conversation with Alasdair (the pub
manager). I booked the Haymarket Tap for 6 people on Friday at
7:30pm, asked about bar snacks and the deposit (£200), confirmed
the booking, and gave a contact number. The trace emitted 8 events:
four `voice.utterance_in` (my messages) and four `voice.utterance_out`
(Alasdair's replies). Each event has `{text, turn, mode}` in its
payload, with `mode: "text"` for my run.

The graceful degradation design is the key choice: `run_voice_mode`
checks for `SPEECHMATICS_KEY` and the `speechmatics` import before
doing anything. If either is missing, it falls through to
`run_text_mode`. This means CI can pass the "voice loop implemented"
check without credentials. The `mode` field in trace events tells
the grader which transport was used, but the event shape is
identical either way.

The ManagerPersona stays in character well — Alasdair responded
with Scottish idiom ("I'll pencil you in", "aye", "laddie") and
consistently asked for a contact number across turns, which is
realistic pub manager behaviour.

## Citations

- `sessions/homework/ex8/sess_e8cff95ecff4/logs/trace.jsonl` — 8 trace events from 4-turn conversation
- `starter/voice_pipeline/voice_loop.py` — `run_voice_mode` with degradation logic
- `starter/voice_pipeline/manager_persona.py` — LLM-backed pub manager persona
