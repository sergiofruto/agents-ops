import os
from dotenv import load_dotenv

load_dotenv()

# Bet filtering thresholds
MIN_PROBABILITY = 0.70
MAX_PROBABILITY = 0.97   # Avoid near-certainties (low ROI)
MIN_VOLUME_24H  = 5_000  # $5K minimum liquidity
MAX_SPREAD      = 0.05   # 5% max bid-ask spread
MIN_SCORE       = 0.65   # Composite score threshold

# Simulation settings
VIRTUAL_BET_SIZE = 100   # $100 simulated per bet
MAX_BETS_PER_SCAN = 5    # Max new bets placed per scan cycle

# Polling intervals
SCAN_INTERVAL_MINUTES  = 30
TRACK_INTERVAL_MINUTES = 15

# Scoring weights (must sum to 1.0)
WEIGHT_PROBABILITY = 0.40
WEIGHT_VOLUME      = 0.25
WEIGHT_STABILITY   = 0.20
WEIGHT_SPREAD      = 0.15

# Edge filter
MIN_EDGE         = float(os.getenv("MIN_EDGE", "0.03"))   # 3% minimum true-vs-market edge
ODDS_API_KEY     = os.getenv("ODDS_API_KEY", "")          # the-odds-api.com free tier

# Kelly sizing (VIRTUAL_BET_SIZE kept as fallback when edge unknown)
VIRTUAL_BANKROLL = 10_000   # total paper bankroll ($)
KELLY_FRACTION   = 0.5      # half-Kelly
MAX_BET_SIZE     = 250      # cap per bet ($)
MIN_BET_SIZE     = 10       # floor per bet ($)

# API endpoints
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "bets.db")

# Mode
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
POLY_ADDRESS     = os.getenv("POLY_ADDRESS", "")
POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY", "")

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 5001
