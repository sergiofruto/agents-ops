import os
from dotenv import load_dotenv

load_dotenv()

# Bet filtering thresholds (Dota-tuned)
MIN_PROBABILITY = 0.60   # Lower ceiling (esports volatile)
MAX_PROBABILITY = 0.85
MIN_VOLUME_24H  = 2_000  # $2K (Dota markets smaller)
MAX_SPREAD      = 0.06   # 6% max bid-ask spread
MIN_SCORE       = 0.55   # Composite score threshold
MIN_EDGE        = 0.07   # 7% edge gate (raised after backtest showed ~5% overconfidence)

# Probability calibration — backtest showed the model overshoots by ~5-6pp at all
# confidence levels; shrink true_prob toward 0.5 before computing edge.
CALIBRATION_FACTOR = 0.90   # true_prob = 0.5 + (raw - 0.5) * CALIBRATION_FACTOR

# Simulation settings
VIRTUAL_BET_SIZE  = 100  # $100 simulated per bet (fallback)
MAX_BETS_PER_SCAN = 3    # Conservative

# Polling intervals
SCAN_INTERVAL_MINUTES  = 20
TRACK_INTERVAL_MINUTES = 10

# Scoring weights (must sum to 1.0)
WEIGHT_EDGE       = 0.45
WEIGHT_FORM       = 0.25
WEIGHT_H2H        = 0.15
WEIGHT_TOURNAMENT = 0.15

# Kelly sizing
VIRTUAL_BANKROLL = 10_000   # total paper bankroll ($)
KELLY_FRACTION   = 0.5      # half-Kelly
MAX_BET_SIZE     = 200      # cap per bet ($)
MIN_BET_SIZE     = 10       # floor per bet ($)

# API endpoints
GAMMA_BASE    = "https://gamma-api.polymarket.com"
CLOB_BASE     = "https://clob.polymarket.com"
OPENDOTA_BASE = "https://api.opendota.com"

# API keys
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")  # stored for future use; no esports on Odds API

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "dota_bets.db")

# Mode
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 5002
