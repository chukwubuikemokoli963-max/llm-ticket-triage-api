# Support Ticket Triage API

## Provider Abstraction
Only three environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`) are the difference between a model running locally via Ollama and one running in a datacentre via OpenRouter. Nobody should ever hard-code a provider.
