import json
import os
import re
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from openai import OpenAI, APIStatusError, APITimeoutError
from src.llm.client import load_system_prompt, PROMPT_VERSION
from src.llm.schema import TriageOutput, CategoryEnum, UrgencyEnum, TeamEnum

LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
QUARANTINE_FILE = LOGS_DIR / "quarantine.jsonl"


def clean_json_text(raw_text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    return match.group(0) if match else cleaned


def log_cost_telemetry(prompt_version: str, model: str, in_tokens: int, out_tokens: int, duration_ms: float, repairs: int):
    """Write structured telemetry to stdout (12-Factor style)."""
    telemetry = {
        "event": "llm_completion",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "total_tokens": in_tokens + out_tokens,
        "duration_ms": round(duration_ms, 2),
        "repair_count": repairs,
    }
    sys.stdout.write(json.dumps(telemetry) + "\n")
    sys.stdout.flush()


def log_to_quarantine(user_text: str, raw_output: str, error_message: str):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input_text": user_text,
        "raw_model_output": raw_output,
        "error": error_message,
    }
    with open(QUARANTINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def call_with_retry(client: OpenAI, **kwargs):
    """
    Selective retry policy:
    - Retries on APITimeoutError, 429, and 5xx errors with exponential backoff + jitter.
    - Fails fast on 400, 401, 403 (never retries bad client credentials or bad requests).
    """
    max_attempts = 3
    base_delay = 1.0

    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except APITimeoutError:
            if attempt == max_attempts:
                raise
            sleep_time = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
            time.sleep(sleep_time)
        except APIStatusError as e:
            # 400, 401, 403 are unrecoverable client errors — fail fast
            if e.status_code in [400, 401, 403]:
                raise e
            # 429 and 5xx are transient — retry with backoff
            if e.status_code == 429 or e.status_code >= 500:
                if attempt == max_attempts:
                    raise e
                # Check for Retry-After header if provided
                retry_after = e.response.headers.get("retry-after")
                if retry_after and retry_after.isdigit():
                    sleep_time = float(retry_after) + random.uniform(0.1, 0.3)
                else:
                    sleep_time = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                time.sleep(sleep_time)
            else:
                raise e


def execute_triage_pipeline(user_text: str) -> tuple[TriageOutput | None, bool]:
    """
    Executes the LLM triage with explicit timeout, smart retries, structured logging,
    and a 1x repair retry loop.
    Returns: (TriageOutput or None, is_timeout_boolean)
    """
    # Explicit 30-second timeout, max_retries=0 so our explicit retry loop handles attempts
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )
    model = os.environ["LLM_MODEL"]
    system_prompt = load_system_prompt()
    safe_user_message = json.dumps({"text": user_text})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": safe_user_message},
    ]

    start_time = time.time()
    repairs = 0
    in_tokens = 0
    out_tokens = 0

    try:
        res = call_with_retry(
            client=client,
            model=model,
            temperature=0.1,
            messages=messages,
        )
    except APITimeoutError:
        return None, True

    if res.usage:
        in_tokens += res.usage.prompt_tokens
        out_tokens += res.usage.completion_tokens

    raw_output = res.choices[0].message.content or ""
    first_error = None

    try:
        cleaned = clean_json_text(raw_output)
        output = TriageOutput.model_validate_json(cleaned)
        duration_ms = (time.time() - start_time) * 1000
        log_cost_telemetry(PROMPT_VERSION, model, in_tokens, out_tokens, duration_ms, repairs)
        return output, False
    except (json.JSONDecodeError, ValidationError) as e:
        first_error = str(e)
        repairs += 1

    # Repair Retry (Exactly once)
    repair_instruction = (
        f"Your previous answer was rejected for this reason:\n{first_error}\n"
        f"Raw rejected response:\n{raw_output}\n\n"
        "Return ONLY corrected JSON matching the schema with allowed enum values."
    )
    repair_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": safe_user_message},
        {"role": "assistant", "content": raw_output},
        {"role": "user", "content": repair_instruction},
    ]

    try:
        repair_res = call_with_retry(
            client=client,
            model=model,
            temperature=0.1,
            messages=repair_messages,
        )
    except APITimeoutError:
        return None, True

    if repair_res.usage:
        in_tokens += repair_res.usage.prompt_tokens
        out_tokens += repair_res.usage.completion_tokens

    raw_repair = repair_res.choices[0].message.content or ""
    duration_ms = (time.time() - start_time) * 1000

    try:
        cleaned_repair = clean_json_text(raw_repair)
        output = TriageOutput.model_validate_json(cleaned_repair)
        log_cost_telemetry(PROMPT_VERSION, model, in_tokens, out_tokens, duration_ms, repairs)
        return output, False
    except (json.JSONDecodeError, ValidationError) as final_err:
        log_cost_telemetry(PROMPT_VERSION, model, in_tokens, out_tokens, duration_ms, repairs)
        log_to_quarantine(user_text, raw_repair, str(final_err))
        return None, False
