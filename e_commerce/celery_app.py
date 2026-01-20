"""
Celery Configuration Module
=========================

Handles asynchronous and scheduled tasks in Django.
"""

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from datetime import timedelta
# Load environment variables
load_dotenv()

# ------------------------------------------------
# 1️⃣ Configure Django settings BEFORE anything else
# ------------------------------------------------
if os.getenv('env', 'dev') == 'prod':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings.dev')

# ------------------------------------------------
# 2️⃣ Setup Django after setting DJANGO_SETTINGS_MODULE
# ------------------------------------------------
import django
django.setup()

# ------------------------------------------------
# 3️⃣ Initialize Celery app
# ------------------------------------------------
app = Celery('e_commerce')

# Load Celery settings from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# ------------------------------------------------
# 4️⃣ Fallback Redis Config (for Render)
# ------------------------------------------------
if not app.conf.get('broker_url'):
    app.conf.broker_url = os.getenv("RENDER_REDIS", "redis://localhost:6379/1")
if not app.conf.get('result_backend'):
    app.conf.result_backend = os.getenv("RENDER_REDIS", "redis://localhost:6379/1")

# ------------------------------------------------
# 5️⃣ Celery Extra Configuration
# ------------------------------------------------
app.conf.update(
    broker_transport_options={'visibility_timeout': 3600},
    result_expires=3600,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Lagos',
    enable_utc=False,
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
)

# ------------------------------------------------
# 6️⃣ Auto-discover tasks from all apps
# ------------------------------------------------
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')


CELERY_BEAT_SCHEDULE = {
    'cleanup-orphaned-carts-hourly': {
        'task': 'stock.tasks.cleanup_orphaned_carts_task',
        'schedule': crontab(minute=0),  # Run every hour
    },
    'cleanup-expired-sessions-daily': {
        'task': 'stock.tasks.cleanup_expired_sessions_and_carts',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'clean-expired-carts': {
        'task': 'stock.tasks.clean_expired_carts',
        'schedule': crontab(hour=1),
    },
    'send-cart-reminders': {
        'task': 'stock.tasks.send_cart_reminders',
        'schedule': crontab(hour=6),
    },
    'update-product-cache': {
        'task': 'stock.tasks.update_product_cache',
        'schedule': crontab(minute=30),
    },
    'scheduler-task-payment-expiry': {
        'task': 'stock.tasks.schedule_payment_expiry_check',
        'schedule': timedelta(minutes=45),  # Every 45 minutes
    },
}