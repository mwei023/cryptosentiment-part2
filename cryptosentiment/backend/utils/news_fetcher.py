# 📁 utils/news_fetcher.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

async def fetch_news(coin_id):
    if not NEWS_API_KEY:
        print("[WARNING] NEWS_API_KEY is missing")
        return []

    url = f"https://newsapi.org/v2/everything?q={coin_id}&apiKey={NEWS_API_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [a["title"] for a in data.get("articles", [])]
    except Exception as e:
        print(f"[ERROR] Failed to fetch news: {e}")
        return []
