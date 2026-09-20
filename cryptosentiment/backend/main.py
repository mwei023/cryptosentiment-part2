import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests
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


def _opt_float(raw):
    """CSV string -> float | None (journal cells are often empty)."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _opt_bool(raw):
    """CSV '1'/'0'/'' -> True/False/None."""
    s = str(raw).strip()
    return True if s == "1" else (False if s == "0" else None)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

# Deployed frontends are unknown at code time (onrender.com subdomain,
# custom domains, previews). Allow-list comes from the env; "*" keeps
# localhost behavior for development. Sentiment endpoints never accept
# credentials-bearing requests, so a broad list is low risk here.
_extra_origins = [
    o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",")
    if o.strip()
]
if "*" in _extra_origins:
    origins = "*"
else:
    origins = origins + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Free Render tier: 512 MB RAM cannot hold FinBERT (torch + BERT-base,
# ~1 GB resident). When DISABLE_HEAVY_MODELS=1 (set in render.yaml),
# sentiment endpoints return 503 with an explanation instead of being
# killed by the OOM reaper mid-request. Unset/"0" = attempt to load.
HEAVY_MODELS_DISABLED = os.getenv("DISABLE_HEAVY_MODELS", "0") == "1"


def _require_heavy_models():
    if HEAVY_MODELS_DISABLED:
        raise HTTPException(
            status_code=503,
            detail=(
                "Sentiment endpoints are disabled on this compute tier: "
                "FinBERT needs >512MB RAM. Upgrade the plan and set "
                "DISABLE_HEAVY_MODELS=0 to enable."
            ),
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
        "available_routes": [
            "/",
            "/health",
            "/cryptos",
            "/analyze-news",
            "/predict/{coin_id}",
            "/confidence/{coin_id}",
            "/history/{coin_id}",
            "/prices/{coin_id}",
            "/research/daily-report",
            "/research/scoreboard",
            "/research/journal",
        ]
    }


@app.get("/health")
def health():
    """Render health check — must be cheap and never touch upstream APIs."""
    return {"status": "ok"}


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
    _require_heavy_models()
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
    _require_heavy_models()
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
    _require_heavy_models()
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


@app.get("/research/daily-report")
def get_daily_report():
    """Return the latest E006 dual-arm daily report JSON."""
    import json
    from research.daily_report import _load_reports, main as generate_report
    reports = _load_reports()
    if reports:
        try:
            with open(reports[-1]) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read latest report file: {e}")
    # Fallback to generating in print-only mode
    return generate_report(["--print-only"])


@app.get("/research/scoreboard")
def get_research_scoreboard():
    """Return the live E006 head-to-head scoreboard between price and info arms."""
    from utils import journal
    return journal.summary()


@app.get("/research/journal")
def get_research_journal():
    """E006 journal ledger: per-row dual-arm signals, settlements and P&L.

    Powers the frontend's cumulative P&L chart and trade log. Returns the
    raw CSV rows (typed/ordered for the chart) plus the summary() stats.
    Unsettled rows are included with null net/win so the frontend can
    show pending trades honestly instead of inventing fills.
    """
    from utils import journal
    rows = journal.read_rows()
    ledger = [
        {
            "date": r["date"],
            "coin_id": r["coin_id"],
            "price": _opt_float(r["price"]),
            "band_position": r["band_position"],
            "signal_price": r["signal_price"],
            "signal_info": r["signal_info"],
            "conf_price": _opt_float(r["conf_price"]),
            "conf_info": _opt_float(r["conf_info"]),
            "net_price": _opt_float(r["net_price"]),
            "net_info": _opt_float(r["net_info"]),
            "win_price": _opt_bool(r["win_price"]),
            "win_info": _opt_bool(r["win_info"]),
        }
        for r in rows
    ]
    return {
        "rows": ledger,
        "summary": journal.summary(),
    }


@app.get("/prices/{coin_id}")
def get_price_history(
    coin_id: str,
    days: int = Query(default=90, ge=2, le=365),
):
    """Daily close history for charts (CoinGecko market_chart passthrough).

    Returns {prices: [[timestamp_ms, close], ...]} oldest-first. Errors
    surface as HTTP codes — 502 when the upstream provider fails, 422
    for invalid ranges — instead of silent empty lists.
    """
    if days < 2:
        raise HTTPException(status_code=422, detail="days must be >= 2")
    try:
        data = get_historical_prices(coin_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream market data unavailable: {e}")
    prices = data.get("prices", [])
    if not prices:
        raise HTTPException(status_code=502, detail="Upstream market data provider returned no data")
    return {"coin_id": coin_id, "days": days, "prices": prices}
