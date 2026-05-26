import os
from dotenv import load_dotenv

load_dotenv()

# LLM
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-haiku-4-5-20251001"  # cheap + fast for categorization
STRATEGY_MODEL = "claude-sonnet-4-6"     # smarter for monthly synthesis

# Financial profile
MONTHLY_INCOME          = float(os.getenv("MONTHLY_INCOME", "5500"))
MONTHLY_SAVINGS_TARGET  = float(os.getenv("MONTHLY_SAVINGS_TARGET", "3000"))
GOAL_TARGET             = float(os.getenv("GOAL_TARGET", "100000"))
INVESTMENT_RETURN_RATE  = 0.07  # 7% annual conservative ETF estimate

# ARS/USD rate — auto-fetched from BCRA if not set
ARS_USD_RATE = float(os.getenv("ARS_USD_RATE", "0")) or None

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")

# Known bills (name, amount_usd, due_day, category)
KNOWN_BILLS = [
    ("Rent",          700.0,  1,  "housing"),
    ("Car Insurance", 120.0,  5,  "transport"),
    ("Medical Plan",  180.0,  10, "health"),
    ("Internet",      100.0,  15, "utilities"),
    ("University",    250.0,  1,  "education"),
    ("Car Gas",       180.0,  0,  "transport"),   # 0 = variable, no fixed due day
    ("Dog Food",      180.0,  0,  "pets"),         # 0 = variable
]

# Expense categories
CATEGORIES = [
    "housing",
    "transport",
    "groceries",
    "food_dining",
    "health",
    "education",
    "pets",
    "utilities",
    "subscriptions",
    "investments",
    "personal_transfers",
    "other",
]

# Known merchant → category mappings (lowercase match)
MERCHANT_CATEGORIES = {
    # Food & dining
    "rappi":           "food_dining",
    "dlo*rappi":       "food_dining",
    "rappipro":        "food_dining",
    "mcdonald":        "food_dining",
    "cabrera":         "food_dining",
    "luccianos":       "food_dining",
    "il magazzino":    "food_dining",
    "nuevo cielo":     "food_dining",
    "mestiza":         "food_dining",
    "bao delivery":    "food_dining",
    "work cooking":    "food_dining",
    "casa rosa":       "food_dining",
    "merpago*delsurhel": "food_dining",
    "delsurhelados":   "food_dining",
    # Groceries
    "carnes san francisco": "groceries",
    "market la plata":      "groceries",
    "dia tienda":           "groceries",
    "pvs*super":            "groceries",
    "merpago*cencosud":     "groceries",
    "melans":               "groceries",
    "3sm*super":            "groceries",
    "pimpollo":             "groceries",
    # Transport
    "appypf":          "transport",
    "combust":         "transport",
    "nafta":           "transport",
    # Health
    "farmacity":       "health",
    "clinica":         "health",
    "veterinaria":     "health",
    "medic":           "health",
    "farmamondongo":   "health",
    # Pets
    "reino animal":    "pets",
    "pumita pet":      "pets",
    "merpago*clinicaveterinari": "pets",
    # Subscriptions
    "google":          "subscriptions",
    "youtube":         "subscriptions",
    "netflix":         "subscriptions",
    "spotify":         "subscriptions",
    # Education
    "uai":             "education",
    "universidad":     "education",
    # Investments
    "fondos comunes":  "investments",
    "super ahorro":    "investments",
    "supergestion":    "investments",
    # Transfers (to known people — noise in expense analysis)
    "sergio gabriel fruto": "personal_transfers",
    "campos akai":          "personal_transfers",
    "samora":               "personal_transfers",
    "parnisar":             "personal_transfers",
    "guzman":               "personal_transfers",
    "mouly":                "personal_transfers",
    "magallanes":           "personal_transfers",
    "nicito":               "personal_transfers",
    "marcos":               "personal_transfers",
}

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "5006"))
