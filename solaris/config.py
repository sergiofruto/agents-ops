import os
from dotenv import load_dotenv

load_dotenv()

POLYMARKET_DB = os.path.join(os.path.dirname(__file__), "../polymarket-agent/bets.db")
DOTA_DB = os.path.join(os.path.dirname(__file__), "../dota-agent/dota_bets.db")
SOLARIS_DB = os.path.join(os.path.dirname(__file__), "solaris.db")
STOCK_WATCHLIST = os.getenv("STOCK_WATCHLIST", "SPY,QQQ,NVDA").split(",")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
WEB_PORT = int(os.getenv("WEB_PORT", "5010"))
