import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FACTCHECK_API_KEY = os.getenv("FACTCHECK_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Which model backend runs the pipeline, and which one takes over if it fails.
LLM_BACKEND = os.getenv("LLM_BACKEND", "claude_cli")
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "gemini")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_CLI_PATH = os.getenv("CLAUDE_CLI_PATH", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

EXTRACT_EFFORT = os.getenv("EXTRACT_EFFORT", "low")
JUDGE_EFFORT = os.getenv("JUDGE_EFFORT", "low")

CACHE_DIR = Path(os.getenv("CACHE_DIR", ROOT / "data"))
CACHE_TTL_DAYS = float(os.getenv("CACHE_TTL_DAYS", "7"))

MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "4"))
MAX_PARALLEL_CLAIMS = int(os.getenv("MAX_PARALLEL_CLAIMS", "3"))
