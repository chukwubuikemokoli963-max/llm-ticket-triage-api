import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from openai import OpenAI
from src.llm.client import load_system_prompt, PROMPT_VERSION
from src.llm.schema import TriageOutput

LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
QUARANTINE_FILE = LOGS_DIR / "quarantine.jsonl"


def clean_json_text(raw_text: str) -> str:
    """Strip markdown code blocks and extract the first JSON object."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    return match.group(0) if match else cleaned


def log_to_quarantine(user_text: str, raw_output: str, error_message: str):
    """Write unrepairable invalid responses to logs/quarantine.jsonl."""
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


def execute_triage_with_repair(user_text: str) -> TriageOutput | None:
    """
    1. Parse and validate against TriageOutput schema.
    2. Repair once and only once if validation or parsing fails.
    3. Quarantine and return None on final failure.
    """
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )
    system_prompt = load_system_prompt()
    safe_user_message = json.dumps({"text": user_text})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": safe_user_message},
    ]

    # Attempt 1: Standard generation
    res = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.1,
        messages=messages,
    )
    raw_output = res.choices[0].message.content or ""

    first_error = None
    try:
        cleaned = clean_json_text(raw_output)
        return TriageOutput.model_validate_json(cleaned)
    except (json.JSONDecodeError, ValidationError) as e:
        first_error = str(e)

    # Attempt 2: Repair retry (once and only once)
    repair_instruction = (
        f"Your previous answer was rejected for this reason:\n{first_error}\n"
        f"Raw rejected response:\n{raw_output}\n\n"
        "Return ONLY corrected JSON matching the schema with allowed enum values. No extra text."
    )

    repair_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": safe_user_message},
        {"role": "assistant", "content": raw_output},
        {"role": "user", "content": repair_instruction},
    ]

    repair_res = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.1,
        messages=repair_messages,
    )
    raw_repair_output = repair_res.choices[0].message.content or ""

    try:
        cleaned_repair = clean_json_text(raw_repair_output)
        return TriageOutput.model_validate_json(cleaned_repair)
    except (json.JSONDecodeError, ValidationError) as final_err:
        log_to_quarantine(user_text, raw_repair_output, str(final_err))
        return None
