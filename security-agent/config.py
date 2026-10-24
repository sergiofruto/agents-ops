"""All settings, loaded from .env via python-dotenv."""
import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

DB_PATH = os.getenv("DB_PATH", str(HERE / "security.db"))
LOG_PATH = str(HERE / "agent.log")

# Dashboard: reachable from this Mac only
WEB_HOST = "127.0.0.1"
WEB_PORT = int(os.getenv("WEB_PORT", "5007"))

# Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_DAILY_CAP_USD = float(os.getenv("AI_DAILY_CAP_USD", "1.0"))
AI_DIGEST_RESERVE_USD = float(os.getenv("AI_DIGEST_RESERVE_USD", "0.33"))
DIGEST_MODEL = os.getenv("DIGEST_MODEL", "claude-haiku-5-5")
CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-haiku-5-5")

# Mac check
PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", str(Path.home() / "Projects")))
RUNAWAY_PROCESS_COUNT = int(os.getenv("RUNAWAY_PROCESS_COUNT", "30"))
