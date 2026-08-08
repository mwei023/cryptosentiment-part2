import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db, init_db
from models.base import Base
# FIX: was `from models.crypto import Base` — Base isn't defined in
# crypto.py, it's imported *into* crypto.py from models.base and just
# happened to be accessible via that indirection. Import it from its
# actual source instead.
from models.prediction import Prediction
from utils.news_fetcher import fetch_news
from utils.sentiment_analyzer import analyze_sentiment
from utils.market_data import get_crypto_list, get_historical_prices
from utils.confidence_calculator import calculate_confidence, calculate_volatility
# FIX: was `from models.prediction import prepare_data, train_prophet_model,
# make_prediction` — that duplicate implementation has been removed from
# models/prediction.py. The canonical pipeline now lives in
# utils/prediction_utils.py.
from utils.prediction_utils import prepare_data, train_prophet_model, make_prediction

app = FastAPI()
router = APIRouter()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FIX: use init_db() from database.py instead of calling
# Base.metadata.create_all(bind=engine) directly here — same effect,
# but keeps table-creation logic in one place.
init_db()


@app.get("/")
def read_root():
    return {
        "message": "Welcome to CryptoSentiment AI API",
        "available_routes": ["/", "/cryptos", "/analyze-news", "/predict/{coin_id}", "/confidence/{coin_id}", "/history/{coin_id}"]
    }


@app.get("/trigger-daily-predictions")
def trigger_predictions():
    from tasks import run_daily_predictions
    task = run_daily_predictions.delay()
    return {"message": "Daily predictions triggered!", "task_id": task.id}


@app.get("/analyze-news")
async def analyze():
    logger.info("🔍 Fetching news for analysis")
    try:
        titles = await fetch_news("Bitcoin")
        if not titles:
            return {"error": "No news articles found for analysis"}

        with ThreadPoolExecutor() as pool:
            sentiments = analyze_sentiment(titles)

        return {"results": sentiments}
    except Exception as e:
        logger.error(f"❌ Error analyzing news: {str(e)}")
        return {"error": str(e)}


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
        result = make_prediction(model, periods=days)
        logger.info(f"✅ Prediction result: {result}")

        return {"prediction": result}
    except Exception as e:
        logger.error(f"❌ Error training model: {str(e)}")
        return {"error": str(e)}


@app.get("/confidence/{coin_id}")
async def get_confidence(coin_id: str):
    logger.info(f"🔍 Calculating confidence for {coin_id}")
    try:
        raw_news = await fetch_news(coin_id)
        titles = raw_news

        sentiments = analyze_sentiment(titles)
        volatility_score = calculate_volatility([s['score'] for s in sentiments])
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
def get_history(coin_id: str, db: Session = Depends(get_db)):
    # FIX: `db` was never injected before — this route referenced a
    # `db` variable that didn't exist anywhere in scope, so this endpoint
    # crashed with NameError on every single call. Now uses FastAPI's
    # dependency injection via Depends(get_db), same pattern as the rest
    # of the app should use.
    logger.info(f"📜 Fetching prediction history for {coin_id}")

    historical_predictions = db.query(Prediction).filter(Prediction.crypto_id == coin_id).all()

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