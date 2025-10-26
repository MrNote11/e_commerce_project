"""
Celery Configuration Module
=========================

Handles asynchronous and scheduled tasks in Django.
"""

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

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
