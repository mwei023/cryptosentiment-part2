from fastapi import FastAPI
from fastapi import Depends
from models.prediction import Prediction
from database import SessionLocal, Base
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from prophet import Prophet
from database import engine
from database import get_db
from models.crypto import Base
from concurrent.futures import ThreadPoolExecutor
from utils.news_fetcher import fetch_news
from utils.sentiment_analyzer import analyze_sentiment
from utils.market_data import get_crypto_list, get_historical_prices
from utils.confidence_calculator import calculate_confidence, calculate_volatility

from utils.confidence_calculator import calculate_confidence
from models.prediction import prepare_data, train_prophet_model, make_prediction
import logging
import httpx
import asyncio

# Initialize FastAPI app
app = FastAPI()
router = APIRouter()

# Add CORS middleware
origins = [
    "http://localhost",
    "http://localhost:3000",  # Allow React dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)


# 🔹 Root Endpoint
@app.get("/")
def read_root():
    return {
        "message": "Welcome to CryptoSentiment AI API",
        "available_routes": ["/", "/cryptos", "/analyze-news", "/predict/{coin_id}", "/confidence/{coin_id}"]
    }

@app.get("/trigger-daily-predictions")
def trigger_predictions():
    from tasks import run_daily_predictions
    task = run_daily_predictions.delay()
    return {"message": "Daily predictions triggered!", "task_id": task.id}

# 🔹 Analyze Sentiment from News
@app.get("/analyze-news")
async def analyze():
    logger.info("🔍 Fetching news for analysis")
    try:
        # Fetch news articles
        titles = await fetch_news("Bitcoin")
        if not titles:
            return {"error": "No news articles found for analysis"}

        # Extract titles
        

        # Analyze sentiment
        lop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            sentiments = analyze_sentiment(titles)
        
        return {"results": sentiments}
    except Exception as e:
        logger.error(f"❌ Error analyzing news: {str(e)}")
        return {"error": str(e)}


# 🔹 Get List of Supported Cryptocurrencies
@app.get("/cryptos")
def list_cryptos():
    return get_crypto_list()

@app.get("/news/{coin_id}")
async def get_news(coin_id: str):
    logger.info(f"🔍 fetching news for {coin_id}")
    try:
        titles = await fetch_news(coin_id)
        if not titles:
            return {"error": "No news found for this coin"}
            
            
        sentiments = analyze_sentiment(titles) 
        return {"news": sentiments}
    except Exception as e:
        logger.error(f"❌ Error fetching news: {str(e)}")
        return {"error": "Failed to fetch news"}
        

# 🔹 Async Price Prediction with Thread Offloading
@app.get("/predict/{coin_id}")
def predict(coin_id: str, days: int = 7):
    logger.info(f"📈 Running prediction for {coin_id} over {days} days")

    try:
        historical_prices = get_historical_prices(coin_id, days=30)

        if not historical_prices["prices"] or len(historical_prices["prices"]) < 2:
            logger.warning("⚠️ Not enough price data for Prophet model")
            return {"error": "Not enough data to make predictions"}

        df = prepare_data(historical_prices["prices"])

        if len(df) < 2:
            logger.warning("⚠️ DataFrame still has less than 2 rows after preparation")
            return {"error": "Data too sparse for training"}

        model = train_prophet_model(df)
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)

        # Format output
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days).to_dict(orient="records")
        logger.info(f"✅ Prediction result: {result}")

        return {"prediction": result}
    except Exception as e:
        logger.error(f"❌ Error training model: {str(e)}")
        return {"error": str(e)}



# 🔹 Calculate Confidence Score
@app.get("/confidence/{coin_id}")
async def get_confidence(coin_id: str):
    logger.info(f"🔍 Calculating confidence for {coin_id}")
    try:
        # Fetch news → Returns list of strings
        raw_news = await fetch_news(coin_id)

        # Wrap them in dictionaries so we can extract `.get("title")`
        articles = [{'title': title} for title in raw_news]

        # Extract titles
        titles = [a['title'] for a in articles]

        # Analyze sentiment
        sentiments = analyze_sentiment(titles)

        # Simulated volatility for now
        volatility_score = calculate_volatility([s['score'] for s in sentiments])

        # Calculate final confidence
        confidence = calculate_confidence(sentiments, volatility_score)

        return {
            "confidence": f"{confidence}%",
            "sentiments_analyzed": len(sentiments),
            "volatility_score": volatility_score
        }

    except Exception as e:
        logger.error(f"❌ Error calculating confidence: {str(e)}")
        return {"error": "Failed to calculate confidence"}


@app.get("/history/{coin_id}")
def get_history(coin_id: str):
    logger.info(f"📜 Fetching prediction history for {coin_id}")
    
    # Replace this with DB query later
    historical_predictions = Prediction.query.filter_by(crypto_id=coin_id).all()
    
    return {
        "predictions": [
            {
                "date": p.generated_at.strftime("%Y-%m-%d"),
                "predicted": p.predicted_price,
                "lower": p.lower_bound,
                "upper": p.upper_bound,
                "confidence": p.confidence_score
            }
            for p in historical_predictions
        ]
    }
