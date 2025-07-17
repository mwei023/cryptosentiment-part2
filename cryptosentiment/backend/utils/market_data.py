# 📁 utils/market_data.py
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3").strip()

def get_crypto_list() -> List[Dict]:
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/list", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch crypto list: {e}")
        return []

def get_historical_prices(coin_id: str, days: int = 30):
    url = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        prices = [[p[0], p[1]] for p in response.json().get("prices", [])]
        return {"prices": prices}
    except requests.RequestException as e:
        print(f"[ERROR] CoinGecko API request failed: {e}")
        return {"prices": []}

def get_latest_price(coin_id: str) -> Optional[float]:
    url = f"{COINGECKO_API_URL}/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get(coin_id, {}).get("usd")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch latest price: {e}")
        return None

def get_coin_info(coin_id: str) -> Dict:
    url = f"{COINGECKO_API_URL}/coins/{coin_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "rank": data.get("market_cap_rank"),
            "description": data.get("description", {}).get("en", "No description available")
        }
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch coin info: {e}")
        return {}