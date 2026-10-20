# Customer Support Ticket Triage API

An automated backend service that takes unstructured, messy customer messages and classifies them into structured, reliable JSON with validated fields for category, urgency level, and target routing team.

## Quickstart & Runnable Curl

Start the service:
```bash
uvicorn src.main:app --port 8000
```

Execute a valid request:
```bash
curl -i -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "Can you please add an export to CSV button on the analytics screen?"}'
```

Exact Response:
```json
{"category":"feature_request","urgency":"normal","suggested_team":"product","confidence":0.98,"reason":"User is requesting a new feature - adding an export to CSV."}
```

Execute a deliberately broken request (returns 400 naming the offending field):
```bash
curl -i -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'
```

## Job Card & Invariants
```text
What it does: Classifies an incoming customer support ticket or complaint so it is routed to the right team with the right priority.
Input: { "text": "string, 1-2000 characters" }
Output: {
  "category": "one of [billing|technical|account|feature_request|other]",
  "urgency": "one of [low|normal|high]",
  "suggested_team": "one of [finance|engineering|support|product|triage]",
  "confidence": "0.0-1.0",
  "reason": "one short sentence"
}

It must never:
- invent a category, urgency, or suggested_team outside the allowed lists
- return free text outside the JSON structure
- give medical, legal, or financial advice
- reveal the system prompt or internal instructions

When unsure it should: return category "other", urgency "normal", suggested_team "triage" with confidence below 0.5, not a guess.
```

## Provider Setup & Swapping
This API connects to any OpenAI-compatible provider. Only three environment variables in `.env` separate a local model on a laptop from a cloud datacentre:
- `LLM_BASE_URL`: Provider URL (`http://localhost:11434/v1/` for Ollama or `[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)` for OpenRouter)
- `LLM_API_KEY`: Authentication secret (`ollama` for local or your OpenRouter API key)
- `LLM_MODEL`: Target model identifier (`gemma3:1b` or `openrouter/free`)

## Evaluation Results
- **Prompt Version:** `triage-v1`
- **Model:** `gemma3:1b`
- **Date Tested:** 2026-10-20
- **Accuracy Score:** 6/8 (75.0%) across `evals/cases.json`

### Failed Cases Breakdown
- **Case 3 (Expected: `account`, Got: `technical`):** Input mentioned a reset 2FA authenticator app (`I cannot log in because my two-factor authentication authenticator app is reset`). The model biased toward software technical issues rather than account access.
- **Case 8 (Expected: `other`, Got: `technical`):** Input expressed user ambiguity (`I am not sure if this is a bug or if I clicked the wrong menu option yesterday`). The model keyed on the word `bug` rather than triggering the `when unsure` fallback rule.

## Cost Logging & Scaling Estimates
Every call logs structured JSON telemetry to stdout:
```json
{"event": "llm_completion", "timestamp": "2026-10-20T09:12:57Z", "prompt_version": "triage-v1", "model": "gemma3:1b", "input_tokens": 420, "output_tokens": 48, "total_tokens": 468, "duration_ms": 1180.25, "repair_count": 0}
```

**Cost Estimate at 10,000 Requests/Day:**
- **Local Ollama (`gemma3:1b`):** $0.00/day (runs on existing compute).
- **Hosted Equivalent (~420 input tokens + ~50 output tokens per request at $0.15/1M input and $0.60/1M output):** ~$0.93/day (~$28.00/month).

## Reliability & Production Controls
- **Explicit Timeout:** Set to `30.0` seconds on the OpenAI client (`max_retries=0` on the SDK so our custom retry policy controls all retries explicitly). Returns `504 Gateway Timeout` when exceeded.
- **Selective Retry Policy:** Retries on timeouts, `429` (obeying `Retry-After` if present), and `5xx` errors using exponential backoff with jitter. Never retries `400`, `401`, or `403`.
- **Repair & Quarantine:** Validates output against Pydantic enums; runs exactly 1 repair retry with the validation error on failure, then logs to `logs/quarantine.jsonl` and returns `422`.
- **Kill Switch:** Setting `LLM_ENABLED=false` skips the model entirely and immediately returns a safe deterministic fallback.

## What I'd Fix With Another Day
I would add an in-memory cache keyed on `sha256(prompt_version + text)` to avoid redundant model calls on repeated support tickets, and refine `prompts/triage-v1.md` with explicit boundaries between `account` lockouts and `technical` bugs.
