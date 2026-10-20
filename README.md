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
