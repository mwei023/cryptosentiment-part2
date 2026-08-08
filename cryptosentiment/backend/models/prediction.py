from sqlalchemy import Column, Integer, String, Float, DateTime
from models.base import Base
from datetime import datetime


class Prediction(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True)
    crypto_id = Column(String(50))  # CoinGecko id, e.g. 'bitcoin'
    predicted_price = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    confidence_score = Column(Float)
    prediction_type = Column(String)  # 'short' or 'long'
    generated_at = Column(DateTime, default=datetime.utcnow)

# FIX: prepare_data / train_prophet_model / make_prediction used to be
# defined HERE *and* in utils/prediction_utils.py — two competing
# implementations, and main.py imported this copy while tasks.py imported
# the other. They were already starting to drift (different Prophet
# settings, different changepoint_prior_scale). Removed here — the
# canonical pipeline logic now lives only in utils/prediction_utils.py.
# main.py has been updated to import from there instead.