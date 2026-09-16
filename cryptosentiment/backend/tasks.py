import logging
from celery import shared_task
from sqlalchemy.orm import Session

from database import SessionLocal
from models.crypto import CryptoAsset
from utils.prediction_utils import run_prediction_pipeline
# FIX: was `from backend.utils.prediction_utils import run_prediction_pipeline`
# — there's no `backend` package in this layout, everything is flat
# under utils/. That import failed at module load time, which meant
# Celery couldn't even register these tasks.

logger = logging.getLogger(__name__)
# FIX: run_daily_predictions() called logger.info(...) but no logger was
# ever created in this file. Crashed with NameError on first run.


@shared_task
def predict_for_crypto(coin_id: str):
    db: Session = SessionLocal()
    try:
        # FIX: was run_prediction_pipeline(db, coin_id, days=7) — wrong
        # order against the function's real signature (coin_id, days, db),
        # and duplicated the `days` keyword. Now matches prediction_utils.py.
        result = run_prediction_pipeline(coin_id, 1, db)
        return {"coin_id": coin_id, "result": result}
    finally:
        db.close()


@shared_task
def run_daily_journal():
    """E006 automation: settle + log all coins, return printable report.

    Same entry point as ``python -m research.daily_report`` — beat
    calls this so the loop runs on its own every morning.
    """
    from research.daily_report import run_daily, build_report, format_report
    logger.info("📰 Running daily journal (E006 dual-arm)")
    logged = run_daily()
    rep = build_report(logged)
    import json
    import os
    reports_dir = os.path.join(os.path.dirname(__file__),
                               "research", "results", "E006", "daily_reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, f"{rep['date']}.json"), "w") as f:
        json.dump(rep, f, indent=2, default=str)
    text = format_report(rep)
    logger.info("\n" + text)
    return {"status": "success", "date": rep["date"], "report": text,
            "logged": {c: {k: r.get(k) for k in
                           ("signal_price", "signal_info", "skipped", "error")
                           if k in r} for c, r in logged.items()}}


@shared_task
def run_daily_predictions():
    logger.info("🔄 Running daily predictions via celery")

    db: Session = SessionLocal()
    try:
        cryptos = db.query(CryptoAsset).all()

        results = []
        for crypto in cryptos:
            # FIX: was using crypto.id (the integer primary key) as the
            # CoinGecko slug, which always 404'd against the CoinGecko API.
            # Now uses the new coingecko_id column (see models/crypto.py).
            logger.info(f"📈 Predicting for {crypto.name} ({crypto.coingecko_id})")
            prediction_result = run_prediction_pipeline(crypto.coingecko_id, 1, db)
            results.append({crypto.coingecko_id: prediction_result})

        return {"status": "success", "predictions": results}
    finally:
        db.close()