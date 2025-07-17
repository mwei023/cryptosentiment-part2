from celery import shared_task
from prophet import Prophet
from utils.market_data import get_historical_prices
from utils.prediction_utils import prepare_data, train_prophet_model, make_prediction
from sqlalchemy.orm import Session
from database import SessionLocal
from models.crypto import CryptoAsset
from backend.utils.prediction_utils import run_prediction_pipeline
from database import SessionLocal, engine, Base
from datetime import datetime


@shared_task
def predict_for_crypto(coin_id: str):
    db: Session = SessionLocal()
    try:
        result = run_prediction_pipeline(db, coin_id, days=7)
        return {"coin_id": coin_id, "result": result}
    finally:
        db.close()

@shared_task
def run_daily_predictions():
    logger.info("🔄 Running daily predictions via celery")
    
    db: Session = SessionLocal()
    try:
        # Get all cryptos from DB
        cryptos = db.query(CryptoAsset).all()
        
        results = []
        for crypto in cryptos:
            logger.info(f"📈 Predicting for {crypto.name} ({crypto.id})")
            prediction_result = run_prediction_pipeline(db, crypto.id, days=7)
            results.append({crypto.id: prediction_result})
        
        return {"status": "success", "predictions": results}
    finally:
        db.close()