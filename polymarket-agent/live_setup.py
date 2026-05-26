#!/usr/bin/env python3
"""
One-time setup script: derive Polymarket CLOB API credentials from your
private key and print them ready to paste into .env.

Run once:
    python live_setup.py

Then add the printed values to your .env file and set DRY_RUN=false.

IMPORTANT: Keep POLY_API_SECRET and POLY_PRIVATE_KEY secret.
           Never commit .env to version control.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()
    address     = os.getenv("POLY_ADDRESS", "").strip()

    if not private_key:
        print("ERROR: POLY_PRIVATE_KEY is not set in .env")
        print("       Add your wallet private key (hex, with or without 0x prefix).")
        sys.exit(1)

    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    try:
        from py_clob_client_v2.client import ClobClient
        from py_clob_client_v2.constants import POLYGON
    except ImportError:
        print("ERROR: py-clob-client not installed.  Run: pip install -r requirements.txt")
        sys.exit(1)

    # Detect wallet type: if POLY_ADDRESS differs from the key's derived address,
    # this is a Magic/proxy wallet (signature_type=1); otherwise plain EOA (type=0).
    from eth_account import Account
    derived = Account.from_key(private_key).address.lower()
    is_proxy = address and address.lower() != derived

    sig_type = 1 if is_proxy else 0
    wallet_type = "Magic/proxy wallet" if is_proxy else "EOA wallet"
    print(f"Detected: {wallet_type} (signature_type={sig_type})")

    print("Connecting to Polymarket CLOB (Polygon mainnet)…")
    client = ClobClient(
        host           = "https://clob.polymarket.com",
        chain_id       = POLYGON,
        key            = private_key,
        signature_type = sig_type,
        funder         = address if is_proxy else None,
    )

    print("Deriving API credentials (deterministic from your key)…")
    try:
        creds = client.derive_api_key()
    except Exception as exc:
        print(f"ERROR: Could not derive API key — {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Add these lines to polymarket-agent/.env:")
    print("=" * 60)
    print(f"POLY_API_KEY={creds.api_key}")
    print(f"POLY_API_SECRET={creds.api_secret}")
    print(f"POLY_API_PASSPHRASE={creds.api_passphrase}")
    print("DRY_RUN=false")
    print("=" * 60)
    print("\nNOTE: These credentials are now registered on Polymarket's servers.")
    print("      Run this script again only if you need to rotate your API key.")


if __name__ == "__main__":
    main()
