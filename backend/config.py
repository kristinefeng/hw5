"""Model, paths, and run limits shared by every Campus Customs agent.

PORTKEY_API_KEY comes from the nearest .env at or above hw5/ (the project root
.env). Every agent uses gpt-6-luna through Portkey's OpenAI-compatible gateway.
gpt-6-luna needs the Responses API for function tools, so agents use
OpenAIResponsesModel rather than the chat-completions model.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import UsageLimits
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

HW_ROOT = Path(__file__).resolve().parents[1]
for folder in [HW_ROOT, *HW_ROOT.parents]:
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)

MODEL_NAME = "gpt-6-luna"  # the only model any agent may use
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MCP_SERVER_PATH = HW_ROOT / "mcp_server" / "server.py"
AUDIT_PATH = Path(os.getenv("CAMPUS_CUSTOMS_AUDIT", HW_ROOT / "output" / "audit_trail.json"))
# Same override the MCP server reads, so the API and the agents always share one database.
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", HW_ROOT / "data" / "campus_customs_new.db"))
ORIGINAL_DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_ORIGINAL_DB", HW_ROOT / "data" / "campus_customs.db"))

RUNS_PATH = Path(os.getenv("CAMPUS_CUSTOMS_RUNS", HW_ROOT / "output" / "runs.json"))

# The Vite dashboard's origin. The regex also admits other localhost ports, since
# Vite moves to 5174+ when 5173 is busy.
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
CASH_CUSHION = 500.0  # warn (not block) when an approved payment leaves less than this

# --- Token and loop limits -------------------------------------------------
# One ticket run (boss + every delegated agent) shares a single usage budget.
TEAM_USAGE_LIMITS = UsageLimits(
    request_limit=30,  # model calls across the whole team for one ticket
    tool_calls_limit=60,  # MCP + delegation calls across the whole team
    total_tokens_limit=150_000,  # hard stop on tokens for one ticket
)
MAX_DELEGATION_DEPTH = 2  # boss -> specialist -> specialist, no deeper
MAX_DELEGATIONS_PER_RUN = 8  # total hand-offs for one ticket
MODEL_SETTINGS = ModelSettings(max_tokens=1_500)  # cap on each single reply
AUDIT_TEXT_LIMIT = 1_500  # characters kept per text field in the audit trail


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Put it in the project root .env.")
    return key


def load_prompt(role: str) -> str:
    return (PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    key = require_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
