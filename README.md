# Support Ticket Triage API

## Provider Abstraction
Only three environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`) are the difference between a model running locally via Ollama and one running in a datacentre via OpenRouter. Nobody should ever hard-code a provider.

## Testing the Endpoint (Stage 1)

### 1. Valid Request
```bash
curl -i -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "I was charged twice for my subscription this month!"}'
```

### 2. Deliberately Broken Request (Missing/Empty `text` field -> 400)
```bash
curl -i -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'
```

## Stage 2 Observations (Prompt v1)
When testing `gemma3:1b` with `prompts/triage-v1.md` across three real inputs (technical bug, account lockout, and an off-topic message), the model followed the field names and closed enum lists accurately and dropped confidence below 0.5 for the off-topic input. However, `gemma3:1b` frequently wraps its JSON response inside markdown code fences (` ```json ... ``` `), proving why raw model output cannot be trusted without Stage 3 parsing and schema validation.
