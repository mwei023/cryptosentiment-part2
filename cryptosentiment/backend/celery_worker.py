from celery import Celery
from celery.schedules import crontab

# FIX: previously did `from models.base import engine, SessionLocal` —
# models/base.py only ever defined `Base = declarative_base()`, it never
# had engine or SessionLocal. That import raised ImportError on worker
# startup, before Celery even got going. engine/SessionLocal live in
# database.py — importing them here also isn't actually necessary for
# celery_worker.py itself (tasks.py handles its own DB sessions), but
# kept for parity / in case you want a sanity check at startup.
from database import engine, SessionLocal  # noqa: F401
import tasks  # noqa: F401  ensures tasks.py's @shared_task functions get registered

celery_app = Celery("tasks", broker="redis://localhost:6379/0")

celery_app.autodiscover_tasks(["tasks"])

celery_app.conf.beat_schedule = {
    'run-daily-predictions': {
        'task': 'tasks.run_daily_predictions',
        'schedule': crontab(hour=0, minute=0),  # every day at midnight UTC
    },
    'run-daily-journal': {
        'task': 'tasks.run_daily_journal',
        'schedule': crontab(hour=0, minute=5),  # 00:05 UTC: settle + log E006 arms
    },
}

celery_app.conf.timezone = 'UTC'

if __name__ == "__main__":
    celery_app.start()

# FIX NOTE: `sys.path.append(os.path.dirname(os.path.abspath('.')))` was
# removed — os.path.abspath('.') resolves relative to the *current
# working directory the process is launched from*, not this file's
# location, so it was fragile (works when you happen to launch celery
# from backend/, breaks otherwise). Run celery from the backend/
# directory, e.g.:
#   celery -A celery_worker.celery_app worker --loglevel=info
#   celery -A celery_worker.celery_app beat --loglevel=info