# backend/models/crypto.py
from models.base import Base
from sqlalchemy import Column, Integer, String, Float, DateTime
 # <-- Importante! This was missing iki kosa ww kwisha😂😂😂

class CryptoAsset(Base):
    __tablename__ = 'crypto_assets'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    symbol = Column(String)
    launched_date = Column(DateTime)
    description = Column(String)