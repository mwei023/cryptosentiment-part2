"""Prophet forecasting pipeline — crypto-realistic configuration.

Brutal-truth notes (why this looks the way it does):
- Crypto trades 24/7/365. There are no weekends, no market holidays, no
  "US holiday" effects. The old code called
  ``model.add_country_holidays(country_name='US')`` — that injected
  stock-market closures into a market that never closes. Removed.
- ``yearly_seasonality=True`` on 30 data points is pure overfit: Prophet
  tries to estimate an annual cycle from one month of data. Disabled.
  With daily CoinGecko data the only defensible periodic component is
  weekly seasonality; daily seasonality needs intraday data.
- Minimum history is enforced (default 180 daily points). Anything less
  and the function raises instead of returning a confident-looking
  garbage forecast. Callers must surface that error honestly.
"""

from sqlalchemy.orm import Session
import logging
import os
from datetime import datetime

# NOTE: Prophet and pandas are imported lazily inside the prophet code
# path (train/prepare), NOT at module top level. prophet pulls in
# torch-sized dependencies (~300+ MB RAM) and the free-tier web
# service has 512 MB — importing it at boot would OOM every deploy for
# a forecaster that is explicitly the non-default research path. The
# default "naive" forecaster needs only stdlib math.

from models.prediction import Prediction

logger = logging.getLogger(__name__)

MIN_HISTORY_DAYS = 180
DEFAULT_HISTORY_DAYS = 365  # fetch a year, require 180 after cleaning
MAX_HORIZON_DAYS = 7


def prepare_data(prices, min_history: int = MIN_HISTORY_DAYS):
    """Clean CoinGecko ``[[timestamp_ms, price], ...]`` into Prophet ``ds/y``.

    Raises:
        ValueError: if fewer than ``min_history`` usable rows remain.
    """
    import pandas as pd  # lazy: see module NOTE

    if not prices or len(prices) < min_history:
        raise ValueError(
            f"Not enough price data: got {len(prices) if prices else 0} rows, "
            f"need >= {min_history} daily points for a defensible fit."
        )

    df = pd.DataFrame(prices, columns=["timestamp", "y"])
    df["ds"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["ds", "y"]].dropna()
    df = df[df["y"] > 0]  # reject zero/negative stub rows
    df = df.sort_values("ds").drop_duplicates(subset="ds").reset_index(drop=True)

    if len(df) < min_history:
        raise ValueError(
            f"Only {len(df)} usable rows after cleaning, need >= {min_history}."
        )
    return df


def train_prophet_model(df):
    """Fit Prophet with crypto-honest settings. No holidays, no yearly cycle."""
    from prophet import Prophet  # lazy: see module NOTE

    if len(df) < MIN_HISTORY_DAYS:
        raise ValueError(
            f"Refusing to train on {len(df)} rows (< {MIN_HISTORY_DAYS} minimum)."
        )
    model = Prophet(
        yearly_seasonality=False,   # cannot estimate annual cycle; no annual cycle in crypto anyway
        weekly_seasonality=True,    # only periodic component defensible on daily data
        daily_seasonality=False,    # needs intraday timestamps; we have daily closes
        changepoint_prior_scale=0.05,  # Prophet default; conservative on noisy crypto
        interval_width=0.8,         # honest 80% intervals, not fake-narrow bands
        mcmc_samples=0,             # MAP fit; full MCMC too slow per-request
    )
    # NOTE: deliberately NO add_country_holidays — crypto never closes.
    model.fit(df)
    return model


def make_prediction(model, periods: int = 1):
    """Forecast ``periods`` days ahead. Capped to ``MAX_HORIZON_DAYS``."""
    if periods < 1 or periods > MAX_HORIZON_DAYS:
        raise ValueError(f"periods must be 1..{MAX_HORIZON_DAYS}, got {periods}.")
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    latest = forecast.tail(periods)

    return [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "predicted": float(row["yhat"]),
            "lower": float(row["yhat_lower"]),
            "upper": float(row["yhat_upper"]),
        }
        for _, row in latest.iterrows()
    ]


def save_prediction(db: Session, coin_id: str, prediction_data: list, confidence: float = 0.0, prediction_type: str = "short"):
    latest = prediction_data[-1]

    db_prediction = Prediction(
        crypto_id=coin_id,
        predicted_price=latest["predicted"],
        lower_bound=latest["lower"],
        upper_bound=latest["upper"],
        confidence_score=confidence,
        prediction_type=prediction_type,
        generated_at=datetime.utcnow()
    )

    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def run_prediction_pipeline(coin_id: str, days: int = 1, db: Session = None,
                            history_days: int = DEFAULT_HISTORY_DAYS,
                            use_forecaster: str = "naive"):
    """End-to-end pipeline: fetch history -> forecast -> FinBERT sentiment -> confidence -> save.

    Args:
        coin_id: CoinGecko slug, e.g. ``"bitcoin"``.
        days: forecast horizon in days (1..7). Only 1-day is
            walk-forward validated; larger values are experimental.
        db: SQLAlchemy session. If None, prediction is returned but not persisted.
        history_days: how much history to request from CoinGecko (default 365
            so >= 180 survive cleaning even with gaps).
        use_forecaster: ``"naive"`` (default, validated: tomorrow = today
            plus empirical volatility bands) or ``"prophet"`` (experimental
            research path — walk-forward shows it loses to naive 1-day).

    Returns a dict with ``prediction`` / ``confidence`` / ``db_id``,
    or ``{"error": ...}`` — never a fake-confident number.
    """
    from utils.market_data import get_historical_prices
    from utils.news_fetcher import fetch_news
    from utils.sentiment_analyzer import analyze_sentiment
    from utils.confidence_calculator import calculate_confidence
    from utils.volatility import calculate_volatility as price_volatility

    if days < 1 or days > MAX_HORIZON_DAYS:
        return {"error": f"horizon must be 1..{MAX_HORIZON_DAYS} days, got {days}."}
    if use_forecaster not in ("naive", "prophet"):
        return {"error": f"use_forecaster must be 'naive' or 'prophet', got {use_forecaster}."}

    logger.info(f"Running prediction for {coin_id} over {days} day(s) [{use_forecaster}]")

    price_data = get_historical_prices(coin_id, days=history_days)
    prices = price_data.get("prices", [])
    if not prices:
        logger.error("No prices returned from CoinGecko")
        return {"error": "No prices returned from CoinGecko"}

    closes = [float(p[1]) for p in prices if p[1] is not None and float(p[1]) > 0]
    if not closes:
        return {"error": "No usable closes returned from CoinGecko"}
    vol = price_volatility(closes)

    if use_forecaster == "naive":
        from datetime import timedelta
        from utils.forecaster import naive_forecast
        try:
            fc = naive_forecast(closes)
        except Exception as e:
            return {"error": f"naive_forecast: {e}"}
        last_ts_ms = prices[-1][0]
        prediction = []
        for i in range(1, days + 1):
            # Multi-day naive bands scale with sqrt(time) — standard
            # random-walk diffusion; flagged experimental beyond day 1.
            import math as _math
            widen = _math.sqrt(i)
            import pandas as _pd
            day = (_pd.to_datetime(last_ts_ms, unit="ms") + timedelta(days=i)).strftime("%Y-%m-%d")
            prediction.append({
                "date": day,
                "predicted": fc["predicted"],
                "lower": fc["predicted"] * _math.exp(-1.2816 * fc["sigma"] * widen),
                "upper": fc["predicted"] * _math.exp(1.2816 * fc["sigma"] * widen),
            })
        history_rows = len(closes)
    else:  # prophet — experimental research path
        try:
            df = prepare_data(prices)
            logger.info(f"Data prepared: {len(df)} rows")
        except Exception as e:
            logger.exception("Error preparing data")
            return {"error": f"prepare_data: {e}"}

        try:
            model = train_prophet_model(df)
            logger.info("Model trained")
        except Exception as e:
            logger.exception("Error training model")
            return {"error": f"train_prophet_model: {e}"}

        try:
            prediction = make_prediction(model, periods=days)
            logger.info(f"Prediction completed with {len(prediction)} entries")
        except Exception as e:
            logger.exception("Error making prediction")
            return {"error": f"make_prediction: {e}"}
        history_rows = len(df)

    # Real fusion point: FinBERT sentiment on headlines + REAL price volatility.
    # SKIP when heavy models are disabled (512MB tiers): loading torch here
    # would OOM-kill the whole service mid-request. Confidence falls back
    # to price-only, same as the no-news path.
    confidence = 0.0
    n_news = 0
    if os.getenv("DISABLE_HEAVY_MODELS", "0") == "1":
        logger.warning("DISABLE_HEAVY_MODELS=1 — confidence computed from price data only")
        try:
            from utils.confidence_calculator import calculate_confidence
            confidence = calculate_confidence([], price_volatility=vol)
        except Exception as e:
            logger.warning(f"Failed to compute price-only confidence: {e}")
    else:
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    titles = pool.submit(asyncio.run, fetch_news(coin_id)).result()
            else:
                titles = asyncio.run(fetch_news(coin_id))
            if titles:
                sentiments = analyze_sentiment(titles)
                n_news = len(sentiments)
                confidence = calculate_confidence(sentiments, price_volatility=vol)
            else:
                logger.warning("No news found — confidence from price data only")
                confidence = calculate_confidence([], price_volatility=vol)
        except Exception as e:
            logger.warning(f"Failed to compute confidence: {e}")

    saved_id = None
    if db is not None:
        try:
            saved_prediction = save_prediction(db, coin_id, prediction, confidence=confidence, prediction_type="short")
            saved_id = saved_prediction.id
            logger.info(f"Prediction saved to DB (ID: {saved_id})")
        except Exception as e:
            logger.warning(f"Failed to save prediction: {e}")
    else:
        logger.info("No DB session — prediction not persisted")

    result = {
        "prediction": prediction,
        "confidence": confidence,
        "db_id": saved_id,
        "forecaster": use_forecaster,
        "history_rows": history_rows,
        "news_articles": n_news,
    }
    if days > 1:
        result["warning"] = (
            f"{days}-day horizon is experimental; only the 1-day horizon "
            "has been walk-forward validated."
        )
    return result
