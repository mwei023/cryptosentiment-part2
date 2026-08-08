# backend/models/crypto.py
from models.base import Base
from sqlalchemy import Column, Integer, String, DateTime


class CryptoAsset(Base):
    __tablename__ = 'crypto_assets'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    symbol = Column(String)

    # FIX: this column did not exist before. tasks.py's
    # run_daily_predictions() was calling get_historical_prices(crypto.id),
    # but crypto.id is the integer primary key (e.g. 1, 2, 3), while
    # CoinGecko's API needs a slug like "bitcoin" or "ethereum".
    # That call would 404 against CoinGecko every single time.
    # This column stores that slug explicitly so it's never ambiguous.
    coingecko_id = Column(String(50), nullable=False, unique=True)

    launched_date = Column(DateTime)
    description = Column(String)

# NOTE: since this adds a new column, you'll need to either drop/recreate
# the crypto_assets table in dev, or run a migration (Alembic) if you
# care about existing data. Also — when you seed CryptoAsset rows going
# forward, coingecko_id must be populated (e.g. "bitcoin", "ethereum").