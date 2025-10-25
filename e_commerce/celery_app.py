"""
Celery Configuration Module
=========================

This module configures Celery for handling asynchronous tasks and periodic task scheduling
in the Django application. It sets up:

1. Redis as the message broker and result backend
2. Task execution settings and timeouts
3. Periodic tasks schedule using Celery Beat
4. Environment-specific configurations

The system handles various scheduled tasks including:
- Investment processing and interest calculations
- Withdrawal processing and verification
- Account management and cleanup
- System maintenance tasks
"""

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from django.utils import timezone
# from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


# Initialize environment variables from .env file
load_dotenv()


import django
django.setup()

# Configure Django settings based on environment
# This ensures Celery uses the correct Django settings (production or development)
if os.getenv('env', 'dev') == 'prod':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings.dev')

# Initialize Celery application
app = Celery('e_commerce')

# Load Celery settings from Django settings
# Using a string means the worker doesn't have to serialize the configuration object,
# improving performance and reducing potential serialization issues
app.config_from_object('e_commerce:settings', namespace='CELERY')

# Fallback Redis configuration if not set in Django settings
# This ensures the application has a working message broker and result backend
if not app.conf.get('broker_url'):
    app.conf.broker_url = 'redis://localhost:6379/1'
if not app.conf.get('result_backend'):
    app.conf.result_backend = 'redis://localhost:6379/1'

# Comprehensive Celery Configuration
app.conf.update(
    # Message Broker Settings
    broker_url='redis://localhost:6379/1',  # Redis database 1 for message broker
    result_backend='redis://localhost:6379/1',  # Redis database 1 for results
    broker_transport_options={'visibility_timeout': 3600},  # 1 hour task visibility
    
    # Result Settings
    result_expires=3600,  # Results expire after 1 hour
    task_serializer='json',  # Use JSON for task serialization
    accept_content=['json'],  # Only accept JSON content
    result_serializer='json',  # Use JSON for result serialization
    
    # Timezone Settings
    timezone='Africa/Lagos',  # Set timezone to Lagos
    enable_utc=False,  # Use local timezone instead of UTC
    
    # Worker Settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    worker_prefetch_multiplier=1,  # Process one task at a time (disable prefetching)
    
    # Task Execution Settings
    task_acks_late=True,  # Only acknowledge tasks after successful completion
    task_reject_on_worker_lost=True,  # Requeue tasks if worker crashes
    task_track_started=True,  # Enable tracking of task start times
    
    # Task Timeout Settings
    task_time_limit=3600,  # Hard limit: Kill task after 1 hour
    task_soft_time_limit=3300,  # Soft limit: Allow graceful shutdown after 55 minutes
)
django.setup()
# Auto-discover tasks from all Django apps
# This searches for and registers tasks.py files in each Django app
app.autodiscover_tasks()