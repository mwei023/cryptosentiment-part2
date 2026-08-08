from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# FIX NOTE: this is the ONLY Base in the whole project now.
# database.py imports it, crypto.py imports it, prediction.py imports it.
# No other file should call declarative_base() again.