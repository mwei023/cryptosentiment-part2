from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in your .env file")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables registered on models.base.Base."""
    Base.metadata.create_all(bind=engine)


# FIX NOTES:
# - This is now the ONLY place engine/SessionLocal/Base wiring happens.
# - Delete backend/db.py entirely — it defined a second, orphaned
#   declarative_base() that nothing should ever import from.
# - Every model (crypto.py, prediction.py) must import Base from
#   models.base, never re-declare it — otherwise create_all() only
#   sees whichever Base happened to get imported last, and tables
#   for the other models silently never get created.