import os
from dotenv import load_dotenv

load_dotenv()

# Bet filtering thresholds
MIN_PROBABILITY = 0.70
MAX_PROBABILITY = 0.97  # Avoid near-certainties (low ROI)
MIN_VOLUME_24H = 5_000  # $5K minimum liquidity
MAX_SPREAD = 0.05  # 5% max bid-ask spread
MIN_SCORE = 0.65  # Composite score threshold

# Simulation / live settings
VIRTUAL_BET_SIZE       = 100                                               # fallback when no edge signal
MAX_NO_SIGNAL_BET_SIZE = float(os.getenv("MAX_NO_SIGNAL_BET_SIZE", "5"))   # cap for edge=N/A bets
MAX_BETS_PER_SCAN      = int(os.getenv("MAX_BETS_PER_SCAN", "5"))          # max new bets per scan
MAX_OPEN_EXPOSURE_PCT  = float(os.getenv("MAX_OPEN_EXPOSURE_PCT", "0.80")) # max open exposure as % of bankroll
MAX_DAYS_TO_EXPIRY     = int(os.getenv("MAX_DAYS_TO_EXPIRY", "180"))       # skip markets resolving > 180 days out

# Polling intervals
SCAN_INTERVAL_MINUTES = 30
TRACK_INTERVAL_MINUTES = 15

# Scoring weights (must sum to 1.0)
WEIGHT_PROBABILITY = 0.40
WEIGHT_VOLUME = 0.20  # -0.05 to fund expiry signal
WEIGHT_STABILITY = 0.15  # -0.05 to fund expiry signal
WEIGHT_SPREAD = 0.15
WEIGHT_EXPIRY = 0.10  # reward near-term resolution (faster capital cycle)

# Edge filter
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.03"))  # 3% minimum true-vs-market edge
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")  # the-odds-api.com free tier

# Same-market re-entry cooldown
MARKET_COOLDOWN_DAYS = int(os.getenv("MARKET_COOLDOWN_DAYS", "7"))

# Stop-loss / take-profit
STOP_LOSS_PPTS    = float(os.getenv("STOP_LOSS_PPTS",    "0.20"))  # close if price drops 20pp from entry
TAKE_PROFIT_PPTS  = float(os.getenv("TAKE_PROFIT_PPTS",  "0.10"))  # close if price rises 10pp from entry

# LLM edge signal (Claude) — used for "other" category and as fallback
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_EDGE_ENABLED = os.getenv("LLM_EDGE_ENABLED", "true").lower() == "true"
LLM_EDGE_MODEL = os.getenv(
    "LLM_EDGE_MODEL", "claude-haiku-4-5-20251001"
)  # cheap + fast

# Kelly sizing (VIRTUAL_BET_SIZE kept as fallback when edge unknown)
VIRTUAL_BANKROLL = float(os.getenv("VIRTUAL_BANKROLL", "10000"))  # bankroll ($)
KELLY_FRACTION = 0.5  # half-Kelly
MAX_BET_SIZE = float(os.getenv("MAX_BET_SIZE", "250"))  # cap per bet ($)
MIN_BET_SIZE = float(os.getenv("MIN_BET_SIZE", "10"))   # floor per bet ($) — Kelly sizing
MIN_LIVE_ORDER_USDC = float(os.getenv("MIN_LIVE_ORDER_USDC", "2.0"))  # CLOB hard minimum (~$1–5 depending on market)

# API endpoints
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "bets.db")

# Mode
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
POLY_ADDRESS = os.getenv("POLY_ADDRESS", "")
POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY", "")
POLY_CHAIN_ID = int(os.getenv("POLY_CHAIN_ID", "137"))  # 137 = Polygon mainnet

# CLOB API credentials (L2 auth) — generate once with live_setup.py
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE = os.getenv("POLY_API_PASSPHRASE", "")

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 5001
