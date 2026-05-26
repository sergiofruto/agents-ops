"""
Santander Argentina PDF bank statement parser.

parse_statement(pdf_path) → list of transaction dicts
import_statement(pdf_path) → parses and inserts into DB, returns (imported, skipped) counts
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pdfplumber

import config
import database

logger = logging.getLogger("parser")

# ARS rate cache
_ars_rate: Optional[float] = None


def get_ars_usd_rate() -> Optional[float]:
    """
    Fetch current ARS/USD rate. Priority:
    1. .env ARS_USD_RATE (manual override)
    2. bluelytics.com.ar API (blue dollar — relevant for Argentine freelancers)
    3. BCRA official API
    4. Hardcoded fallback (~1100)
    """
    global _ars_rate
    if _ars_rate:
        return _ars_rate
    if config.ARS_USD_RATE:
        _ars_rate = config.ARS_USD_RATE
        logger.info("ARS/USD rate from config: %.2f", _ars_rate)
        return _ars_rate

    import requests

    # Try bluelytics (blue dollar rate — more relevant for freelancers)
    try:
        resp = requests.get("https://api.bluelytics.com.ar/v2/latest", timeout=8)
        data = resp.json()
        rate = float(data["blue"]["value_sell"])
        _ars_rate = rate
        logger.info("ARS/USD blue rate from bluelytics: %.2f", rate)
        return _ars_rate
    except Exception as exc:
        logger.debug("bluelytics failed: %s", exc)

    # Try BCRA official
    try:
        resp = requests.get(
            "https://api.bcra.gob.ar/estadisticas/v2.0/datosvariable/4/2024-01-01/2099-01-01",
            timeout=10,
            verify=False,
        )
        data = resp.json()
        results = data.get("results", [])
        if results:
            _ars_rate = float(results[-1]["valor"])
            logger.info("ARS/USD official rate from BCRA: %.2f", _ars_rate)
            return _ars_rate
    except Exception as exc:
        logger.debug("BCRA API failed: %s", exc)

    # Hardcoded fallback
    _ars_rate = 1100.0
    logger.warning("ARS/USD rate: using fallback %.2f — set ARS_USD_RATE in .env to override", _ars_rate)
    return _ars_rate


def _categorize(description: str) -> str:
    """Map description to category using known merchant map, then return 'other'."""
    desc_lower = description.lower()
    for keyword, category in config.MERCHANT_CATEGORIES.items():
        if keyword.lower() in desc_lower:
            return category
    return "other"


def _parse_ars_amount(text: str) -> Optional[float]:
    """Parse '$  1.234,56' or '-$ 1.234,56' → float (negative if expense)."""
    text = text.strip()
    negative = text.startswith("-")
    # Remove currency symbols and spaces
    text = re.sub(r"[$\s]", "", text)
    text = text.lstrip("-")
    # Argentine format: dots as thousands separator, comma as decimal
    text = text.replace(".", "").replace(",", ".")
    try:
        value = float(text)
        return -value if negative else value
    except ValueError:
        return None


def _parse_date(text: str) -> Optional[str]:
    """Parse 'DD/MM/YY' or 'DD/MM/YYYY' → 'YYYY-MM-DD'."""
    text = text.strip()
    m = re.match(r"(\d{2})/(\d{2})/(\d{2,4})$", text)
    if not m:
        return None
    day, month, year = m.groups()
    if len(year) == 2:
        year = "20" + year
    return f"{year}-{month}-{day}"


def parse_statement(pdf_path: str) -> list[dict]:
    """
    Parse a Santander Argentina PDF bank statement.
    Returns list of transaction dicts:
      {date, description, amount_ars, amount_usd, is_income, raw_text}
    """
    transactions = []
    path = Path(pdf_path)
    if not path.exists():
        logger.error("PDF not found: %s", pdf_path)
        return []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                lines = text.split("\n")
                _parse_page_lines(lines, transactions, page_num)
    except Exception as exc:
        logger.error("Failed to parse PDF %s: %s", pdf_path, exc)

    logger.info("Parsed %d transactions from %s", len(transactions), path.name)
    return transactions


def _parse_page_lines(lines: list[str], transactions: list[dict], page_num: int) -> None:
    """
    Extract transactions from Santander Argentina statement page lines.

    The PDF renders each transaction across 1-3 lines:
      Line A (transaction): [DATE] [COMPROBANTE] DESCRIPTION  -$AMOUNT  $BALANCE
      Line B (merchant):    Merchant name - tarj nro. XXXX
      Line C (date-only):   DD/MM/YY  (sometimes the date appears alone)

    We detect transaction lines by the pattern: AMOUNT + BALANCE at end of line.
    The transaction amount is the one with a possible '-' sign; balance is always positive.
    """
    # Matches: (-$ 1.234,56 or $ 1.234,56) followed by whitespace then ($ BALANCE) at EOL
    tx_pattern = re.compile(
        r"(-?\$\s*[\d\.]+,\d{2})\s+\$\s*[\d\.]+,\d{2}\s*$"
    )
    date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{2,4})\s*")
    skip_keywords = [
        "saldo inicial", "saldo total", "fecha comprobante",
        "caja de ahorro", "cuenta corriente", "saldo en cuenta",
        "desde:", "hasta:", "período", "monto total", "pagos totales",
        "total en pesos", "total en dólares", "salvo error",
        "movimientos en pesos", "movimientos en dólares",
        "traspaso entre cuentas",
    ]

    current_date: Optional[str] = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if any(kw in line.lower() for kw in skip_keywords):
            continue

        # Update current date if this line starts with a date
        dm = date_pattern.match(line)
        if dm:
            parsed = _parse_date(dm.group(1))
            if parsed:
                current_date = parsed

        # Look for transaction amount + balance pattern
        tx_m = tx_pattern.search(line)
        if not tx_m:
            continue

        if not current_date:
            continue

        raw_amount = tx_m.group(1)
        # Determine sign: negative = expense, positive = income
        is_expense = "-" in raw_amount
        amount_ars = _parse_ars_amount(raw_amount)
        if amount_ars is None:
            continue
        amount_ars = abs(amount_ars)
        if amount_ars < 1.0:
            continue

        # Extract description from same line (before the amounts)
        desc_part = line[:tx_m.start()].strip()
        # Remove leading date if present
        desc_part = date_pattern.sub("", desc_part).strip()
        # Remove leading comprobante number (5+ digit sequence)
        desc_part = re.sub(r"^\d{5,}\s*", "", desc_part).strip()

        # Look ahead for merchant name continuation (next non-date, non-amount line)
        merchant = ""
        if i < len(lines):
            next_line = lines[i].strip()
            if next_line and not tx_pattern.search(next_line) and not date_pattern.match(next_line):
                merchant = next_line
                # Strip trailing card info
                merchant = re.sub(r"\s*-\s*tarj nro\.\s*\d+", "", merchant, flags=re.IGNORECASE).strip()
                i += 1

        # Build final description
        if merchant and merchant.lower() not in desc_part.lower():
            description = f"{desc_part} {merchant}".strip() if desc_part else merchant
        else:
            description = desc_part or merchant

        # Remove duplicate whitespace
        description = re.sub(r"\s+", " ", description).strip()
        if not description or len(description) < 3:
            continue

        transactions.append({
            "date":        current_date,
            "description": description,
            "amount_ars":  amount_ars,
            "amount_usd":  None,
            "is_income":   not is_expense,
            "raw_text":    line,
        })


def import_statement(pdf_path: str, ars_usd_rate: Optional[float] = None) -> tuple[int, int]:
    """
    Parse PDF and insert transactions into DB.
    Returns (imported_count, skipped_count).
    Only imports expenses (not income/transfers received).
    """
    if ars_usd_rate is None:
        ars_usd_rate = get_ars_usd_rate()

    transactions = parse_statement(pdf_path)
    imported = 0
    skipped = 0

    for tx in transactions:
        # Skip income entries (we track expenses, not income)
        if tx["is_income"]:
            continue

        # Convert ARS to USD if rate available
        amount_usd = None
        if ars_usd_rate and tx["amount_ars"]:
            amount_usd = round(tx["amount_ars"] / ars_usd_rate, 2)

        category = _categorize(tx["description"])

        saved = database.save_expense(
            date=tx["date"],
            description=tx["description"],
            amount_ars=tx["amount_ars"],
            amount_usd=amount_usd,
            category=category,
            source="santander",
            raw_text=tx["raw_text"],
        )
        if saved:
            imported += 1
        else:
            skipped += 1

    logger.info(
        "Statement import complete: %d imported, %d skipped (duplicates)",
        imported, skipped,
    )
    return imported, skipped
