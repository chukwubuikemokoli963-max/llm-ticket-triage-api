import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROMPT_VERSION = "triage-v1"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / f"{PROMPT_VERSION}.md"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def call_triage_model(user_text: str) -> str:
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )
    system_prompt = load_system_prompt()

    # Keep untrusted user content in the user message and JSON-encode it
    safe_user_message = json.dumps({"text": user_text})

    res = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": safe_user_message},
        ],
    )
    return res.choices[0].message.content or ""
