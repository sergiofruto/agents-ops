"""
Silicon Intel — configuration loaded from .env.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API keys
ALPHA_VANTAGE_KEY: str  = os.getenv("ALPHA_VANTAGE_KEY", "")
ANTHROPIC_API_KEY: str  = os.getenv("ANTHROPIC_API_KEY", "")

# ── Intelligence settings ─────────────────────────────────────────────────────

# Semiconductor ticker watchlist (price-mover signals)
SEMICON_WATCHLIST: list[str] = [s.strip() for s in os.getenv(
    "SEMICON_WATCHLIST",
    "NVDA,AMD,INTC,TSM,ASML,AVGO,AMAT,KLAC,LRCX,MRVL,SMCI,ARM,MU,WDC",
).split(",") if s.strip()]

# Twitter intelligence accounts (handle → description)
TWITTER_ACCOUNTS: dict[str, str] = {
    "zephyr_z9":       "Semiconductor supply chain — components, substrates, fab capacity",
    "TechInsightsInc": "Chiplet / die teardown + process node analysis",
    "SemiAnalysis":    "Foundry economics, AI chip demand, CoWoS/HBM deep dives",
    "IanCutress":      "CPU/GPU architecture + fab process coverage",
    "dylan522p":       "GPU supply chain + VRAM component tracking",
}

# Intel collection intervals
INTEL_SCAN_INTERVAL_MINUTES: int = int(os.getenv("INTEL_SCAN_INTERVAL_MINUTES", "60"))
BRIEF_INTERVAL_HOURS:        int = int(os.getenv("BRIEF_INTERVAL_HOURS",        "6"))

# Price mover threshold for semicon alerts
PRICE_MOVER_THRESHOLD_PCT: float = float(os.getenv("PRICE_MOVER_THRESHOLD_PCT", "3.0"))

# ── Legacy stock-agent settings (kept for compatibility) ──────────────────────

STOCK_WATCHLIST: list[str]  = [s.strip() for s in os.getenv("STOCK_WATCHLIST", "NVDA,TSM,ASML,AVGO,AMAT,KLAC").split(",") if s.strip()]
CRYPTO_WATCHLIST: list[str] = [s.strip() for s in os.getenv("CRYPTO_WATCHLIST", "BTC,ETH,SOL").split(",") if s.strip()]

VIRTUAL_BANKROLL:    float = float(os.getenv("VIRTUAL_BANKROLL",    "10000.0"))
MAX_POSITION_PCT:    float = float(os.getenv("MAX_POSITION_PCT",    "0.10"))
MAX_OPEN_POSITIONS:  int   = int(os.getenv("MAX_OPEN_POSITIONS",    "5"))
STOP_LOSS_PCT:       float = float(os.getenv("STOP_LOSS_PCT",       "0.07"))
TAKE_PROFIT_PCT:     float = float(os.getenv("TAKE_PROFIT_PCT",     "0.20"))

MIN_CONFIDENCE:   float = float(os.getenv("MIN_CONFIDENCE",   "0.65"))
MIN_RULE_SIGNALS: int   = int(os.getenv("MIN_RULE_SIGNALS",   "2"))

SCAN_INTERVAL_MINUTES:  int = int(os.getenv("SCAN_INTERVAL_MINUTES",  "60"))
TRACK_INTERVAL_MINUTES: int = int(os.getenv("TRACK_INTERVAL_MINUTES", "15"))

# Web UI
WEB_HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT: int = int(os.getenv("WEB_PORT", "5005"))

# Paths
DB_PATH: str = "positions.db"
