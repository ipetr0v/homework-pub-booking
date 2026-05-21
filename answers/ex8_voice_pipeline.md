# Ex8 — Voice pipeline

## Your answer

The voice pipeline has two modes sharing the same trace event contract.
I ran text mode (`make ex8-text`, session `sess_a8ca30e9ff53`) which
reads from stdin and gets replies from the ManagerPersona backed by
Llama-3.3-70B. Voice mode would use Speechmatics STT + Rime TTS but
degrades to text mode when the API keys aren't set.

In my session I had a 2-turn conversation with Alasdair (the pub
manager). The trace emitted 4 events: two `voice.utterance_in`
(my messages) and two `voice.utterance_out` (Alasdair's replies).
Each event has `{text, turn, mode}` in its payload, with `mode:
"text"` in my case. Example from the trace:

```json
{"event_type": "voice.utterance_in", "payload": {"text": "Hi, I'd like to book a table for 6 people this Friday at 7:30pm", "turn": 0, "mode": "text"}}
{"event_type": "voice.utterance_out", "payload": {"text": "Aye, we can do that. I'll pencil you in for Friday at 7:30pm. What's the contact number?", "turn": 0, "mode": "text"}}
```

The graceful degradation design is the key choice: `run_voice_mode`
checks for `SPEECHMATICS_KEY` and the `speechmatics` import before
doing anything. If either is missing, it falls through to
`run_text_mode`. This means CI can pass the "voice loop implemented"
check without credentials. The `mode` field in trace events tells
the grader which transport was used, but the event shape is
identical either way.

## Citations

- `sess_a8ca30e9ff53/logs/trace.jsonl` — 4 trace events from my text-mode conversation
- `starter/voice_pipeline/voice_loop.py` — `run_voice_mode` with degradation logic
- `starter/voice_pipeline/manager_persona.py` — LLM-backed pub manager persona

