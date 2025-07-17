import os
import sys
from celery import Celery
from celery.schedules import crontab

sys.path.append(os.path.dirname(os.path.abspath('.')))

# Import your DB and models
from models.base import engine, SessionLocal
from models.prediction import Prediction
from utils.market_data import get_historical_prices
from utils.prediction_utils import prepare_data, train_prophet_model, make_prediction

# Initialize Celery
celery_app = Celery("tasks", broker="redis://localhost:6379/0")

# Load tasks automatically
celery_app.autodiscover_tasks()

# Optional: Add periodic tasks
celery_app.conf.beat_schedule = {
    'run-daily-predictions': {
        'task': 'tasks.run_daily_predictions',
        'schedule': crontab(hour=0, minute=0),  # Runs every day at midnight
    },
}

celery_app.conf.timezone = 'UTC'
if __name__ == "__main__":
    celery_app.start()