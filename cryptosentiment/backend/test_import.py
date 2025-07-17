# backend/test_import.py
from database import engine
from models.base import Base
from models.crypto import CryptoAsset
from models.prediction import Prediction
from utils.market_data import get_crypto_list

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
print(get_crypto_list()[:5])  # Print first 5 cryptos