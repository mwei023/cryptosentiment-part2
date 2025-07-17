import pandas as pd
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from models.base import Base
from prophet import Prophet
from datetime import datetime

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    crypto_id = Column(String(50))  # Use string for CoinGecko IDs like 'bitcoin'
    predicted_price = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    confidence_score = Column(Float)
    prediction_type = Column(String)  # 'short' or 'long'
    generated_at = Column(DateTime, default=datetime.utcnow)

def prepare_data(prices):
    """Converts raw price list from CoinGecko into Prophet-compatible DataFrame"""
    if not prices or len(prices) < 2:
        raise ValueError("Not enough data for prediction")

    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["ds"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["y"] = df["price"]
    df = df.dropna(subset=["ds"])
    return df[["ds", "y"]]

def train_prophet_model(df):
    print("Raw input data:", df.head())  # Debugging line to check input data

    if len(df) < 2:
        raise ValueError(f"Not enough data for prediction. Only {len(df)} rows found.")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10.0
    )
    model.add_country_holidays(country_name='US')
    model.fit(df)
    return model
def make_prediction(model, periods=7):
    """Make future prediction using trained Prophet model"""
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    
    # Format output for frontend
    latest = forecast.tail(periods)
    return latest[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict(orient="records")