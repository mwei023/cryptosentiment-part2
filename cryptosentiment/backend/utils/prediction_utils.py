from sqlalchemy.orm import Session
from celery import shared_task
import logging
from prophet import Prophet
import pandas as pd
from datetime import datetime

from models.prediction import Prediction

logger = logging.getLogger(__name__)

def prepare_data(prices):
    if not prices or len(prices) < 2:
        raise ValueError("Not enough price data to train model")
    
    df = pd.DataFrame(prices, columns=["timestamp", "y"])
    df["ds"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["ds", "y"]]
    return df

def train_prophet_model(df):
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True
    )
    model.add_country_holidays(country_name='US')
    model.fit(df)
    return model

def make_prediction(model, periods=7):
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    latest = forecast.tail(periods)

    return [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "predicted": row["yhat"],
            "lower": row["yhat_lower"],
            "upper": row["yhat_upper"]
        }
        for _, row in latest.iterrows()
    ]

def save_prediction(db: Session, coin_id: str, prediction_data: list, confidence: float=0.0, prediction_type: str = "short"):
    latest = prediction_data[-1]

    db_prediction = Prediction(
        crypto_id=coin_id,
        predicted_price=latest["predicted"],
        lower_bound=latest["lower"],
        upper_bound=latest["upper"],
        confidence_score=0.95,  # Placeholder for actual confidence score utaitafuta badae for this
        prediction_type=prediction_type,
        generated_at=datetime.utcnow()
    )

    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction

def run_prediction_pipeline(coin_id: str, days: int, db: Session):
    from utils.market_data import get_historical_prices

    logger.info(f"📈 Running prediction for {coin_id} over {days} days")

    prices = get_historical_prices(coin_id, days=30)
    if not prices:
        logger.error("No prices returned from CoinGecko")
        return {"error": "No prices returned from CoinGecko"}

    try:
        df = prepare_data(prices)
        logger.info("✅ Data prepared for model")
    except Exception as e:
        logger.exception("❌ Error preparing data")
        return {"error": f"prepare_data: {e}"}

    try:
        model = train_prophet_model(df)
        logger.info("✅ Model trained")
    except Exception as e:
        logger.exception("❌ Error training model")
        return {"error": f"train_prophet_model: {e}"}

    try:
        prediction = make_prediction(model, periods=days)
        logger.info(f"✅ Prediction completed with {len(prediction)} entries")
    except Exception as e:
        logger.exception("❌ Error making prediction")
        return {"error": f"make_prediction: {e}"}

    try:
        saved_prediction = save_prediction(db, coin_id, prediction, prediction_type="short")
        logger.info(f"💾 Prediction saved to DB (ID: {saved_prediction.id})")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save prediction: {e}")

    return {
        "prediction": prediction,
        "db_id": saved_prediction.id if 'saved_prediction' in locals() else None
    }