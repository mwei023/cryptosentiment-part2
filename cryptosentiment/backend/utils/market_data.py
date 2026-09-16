# 📁 utils/market_data.py — CoinGecko with honest failures, retries, rate-limit respect.
import os
import time
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3").strip()
HEADERS = {"User-Agent": "CryptoSentiment/0.2 (research prototype)"}


def _get(url, params=None, tries=3):
    last_err = None
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                wait = 2 ** attempt * 5  # 5, 10, 20s — free tier throttles hard
                print(f"[WARN] CoinGecko 429 rate-limited, sleeping {wait}s (try {attempt+1}/{tries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_err = e
            print(f"[ERROR] CoinGecko request failed (try {attempt+1}/{tries}): {e}")
            time.sleep(2 ** attempt)
    raise requests.RequestException(f"CoinGecko unreachable after {tries} tries: {last_err}")


def get_crypto_list() -> List[Dict]:
    try:
        return _get(f"{COINGECKO_API_URL}/coins/list")
    except requests.RequestException:
        return []


def get_historical_prices(coin_id: str, days: int = 365):
    """Daily market_chart history. Raises on failure instead of silently
    returning [] — callers decide how to surface it. (Old code swallowed
    429s into empty lists, which downstream misread as 'no data'.)"""
    if days < 2:
        raise ValueError("days must be >= 2")
    # CoinGecko free: daily interval auto for >90d; force daily for consistency.
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    try:
        data = _get(f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart", params=params)
    except requests.RequestException as e:
        print(f"[ERROR] CoinGecko market_chart failed for {coin_id}: {e}")
        return {"prices": [], "error": str(e)}
    raw = data.get("prices", []) if isinstance(data, dict) else []
    prices = [[p[0], p[1]] for p in raw if len(p) >= 2 and p[1] is not None and float(p[1]) > 0]
    if not prices:
        print(f"[WARN] CoinGecko returned no usable prices for {coin_id}")
    return {"prices": prices}


def get_latest_price(coin_id: str) -> Optional[float]:
    try:
        data = _get(f"{COINGECKO_API_URL}/simple/price",
                    params={"ids": coin_id, "vs_currencies": "usd"})
        return data.get(coin_id, {}).get("usd")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch latest price: {e}")
        return None


def get_coin_info(coin_id: str) -> Dict:
    try:
        data = _get(f"{COINGECKO_API_URL}/coins/{coin_id}")
        return {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "rank": data.get("market_cap_rank"),
            "description": data.get("description", {}).get("en", "No description available")
        }
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch coin info: {e}")
        return {}
