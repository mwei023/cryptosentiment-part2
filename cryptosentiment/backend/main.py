import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Depends, APIRouter, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from utils.confidence_calculator import calculate_confidence
from utils.volatility import calculate_volatility as price_volatility
from utils.prediction_utils import run_prediction_pipeline

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

# FIX: use init_db() at import time instead of calling
# Base.metadata.create_all(bind=engine) directly here — same effect,
# but keeps table-creation logic in one place.
init_db()


# ---------------------------------------------------------------------------
# Error handling
#
# FIX: previously every endpoint wrapped its body in `try/except Exception`
# and returned {"error": ...} with HTTP status 200. Consequences:
#   - axios never threw, so the frontend silently showed empty panels
#   - "error" responses were indistinguishable from success payloads
#   - raw exception strings (str(e)) leaked internal details to clients
#   - nothing was monitorable (no non-2xx status codes to alert on)
#
# Now:
#   - expected, client-actionable failures raise HTTPException with the
#     correct status code (404 / 422 / 502 / 503)
#   - unexpected exceptions bubble up to the global handler below → 500,
#     with full details logged server-side and a generic body returned
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def read_root():
    return {
        "message": "Welcome to CryptoSentiment AI API",
        "available_routes": ["/", "/cryptos", "/analyze-news", "/predict/{coin_id}", "/confidence/{coin_id}", "/history/{coin_id}"]
    }


@app.get("/trigger-daily-predictions")
def trigger_predictions():
    from tasks import run_daily_predictions
    try:
        task = run_daily_predictions.delay()
    except Exception as e:
        # Typical cause: Redis broker not running (kombu OperationalError).
        logger.error(f"Failed to enqueue daily predictions: {e}")
        raise HTTPException(
            status_code=503,
            detail="Prediction service unavailable: task broker not reachable",
        )
    return {"message": "Daily predictions triggered!", "task_id": task.id}


@app.get("/analyze-news")
async def analyze():
    logger.info("🔍 Fetching news for analysis")
    titles = await fetch_news("Bitcoin")

    if not titles:
        raise HTTPException(status_code=404, detail="No news articles found for analysis")

    # CPU-bound transformer inference stays off the event loop.
    # NOTE: pool.submit (not pool.map) — analyze_sentiment takes the whole
    # list in one call; mapping it per-title would feed it single strings.
    with ThreadPoolExecutor() as pool:
        sentiments = pool.submit(analyze_sentiment, titles).result()

    return {"results": sentiments}


@app.get("/cryptos")
def list_cryptos():
    # get_crypto_list() swallows RequestException and returns [] on upstream
    # failure, so an empty result realistically means CoinGecko is down or
    # rate-limiting us — surface that as 502, not a silent empty 200.
    cryptos = get_crypto_list()
    if not cryptos:
        logger.warning("⚠️ CoinGecko returned no crypto list data")
        raise HTTPException(status_code=502, detail="Upstream market data provider returned no data")
    return cryptos


@app.get("/news/{coin_id}")
async def get_news(coin_id: str):
    logger.info(f"🔍 fetching news for {coin_id}")

    titles = await fetch_news(coin_id)
    if not titles:
        # Could be a bad coin id or a missing/invalid NEWS_API_KEY —
        # either way there is nothing to return. 404, not {"error": 200}.
        raise HTTPException(status_code=404, detail=f"No news found for coin '{coin_id}'")

    sentiments = analyze_sentiment(titles)
    return {"news": sentiments}


@app.get("/predict/{coin_id}")
def predict(
    coin_id: str,
    # 1-day horizon is the only walk-forward-validated setting.
    # Up to 7 allowed but flagged experimental by the pipeline.
    days: int = Query(default=1, ge=1, le=7),
    # Validated default forecaster is naive+vol-bands; Prophet kept
    # as a research path. Walk-forward (BTC/ETH/SOL, 12 folds each):
    # naive MAE beats Prophet 3-6x at 1-day, Prophet direction = 50%.
    forecaster: str = Query(default="naive", pattern="^(naive|prophet)$"),
    db: Session = Depends(get_db),
):
    logger.info(f"📈 Running prediction for {coin_id} over {days} day(s) [{forecaster}]")
    result = run_prediction_pipeline(coin_id, days=days, db=db, use_forecaster=forecaster)
    if "error" in result:
        err = result["error"]
        if "Not enough price data" in err or "usable rows" in err:
            raise HTTPException(status_code=422, detail=err)
        if "No prices returned" in err:
            raise HTTPException(status_code=502, detail=err)
        raise HTTPException(status_code=422, detail=err)
    return result


@app.get("/confidence/{coin_id}")
async def get_confidence(coin_id: str):
    logger.info(f"🔍 Calculating confidence for {coin_id}")

    titles = await fetch_news(coin_id)
    if not titles:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for coin '{coin_id}'; cannot calculate confidence",
        )

    sentiments = analyze_sentiment(titles)
    # Volatility from REAL price history, not sentiment-score dispersion.
    price_data = get_historical_prices(coin_id, days=90)
    closes = [p[1] for p in price_data.get("prices", [])]
    vol = price_volatility(closes)
    confidence = calculate_confidence(sentiments, price_volatility=vol)

    return {
        "confidence": f"{confidence}%",
        "sentiments_analyzed": len(sentiments),
        "volatility_score": round(vol, 6),
        "note": "Heuristic score (agreement/volatility/sample-size); not a calibrated probability.",
    }


@app.get("/history/{coin_id}")
def get_history(coin_id: str, db: Session = Depends(get_db)):
    # FIX: `db` was never injected before — this route referenced a
    # `db` variable that didn't exist anywhere in scope, so this endpoint
    # crashed with NameError on every single call. Now uses FastAPI's
    # dependency injection via Depends(get_db).
    logger.info(f"📜 Fetching prediction history for {coin_id}")

    historical_predictions = db.query(Prediction).filter(Prediction.crypto_id == coin_id).all()

    # NOTE: an empty history is a valid state (200 with an empty list),
    # not a 404 — there is no registry of valid coin ids, so "unknown
    # coin" and "coin with no predictions yet" are indistinguishable.
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
