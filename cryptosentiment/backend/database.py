from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in your .env file")

# Render Postgres provisions `postgres://` URLs; SQLAlchemy 1.4+ refuses
# that scheme for psycopg2, and Render's `?sslmode=require` query param is
# only understood by psycopg2 when the URL uses `postgresql://`. Normalize
# both without touching local `postgresql://` URLs.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

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