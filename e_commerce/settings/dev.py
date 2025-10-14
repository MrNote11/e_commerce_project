print('dev.py')

from .base import * # noqa
import ssl  # noqa: E402
import os  # noqa: E402
from .base import env
import dj_database_url
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-uwlel0vl1i5zsjo@z!z-*0m_k#zpb%cp!_75ge_t*!a(b6%e_r"
# SECURITY WARNING: don't run with debug turned on in production!

VERCEL_APP_URL = 'https://tm30-ecom-web-app-beta.vercel.app'

ENNIE_LOCALHOST_1 =  'http://localhost:5173'

ENNIE_LOCALHOST_2 =  'http://localhost:5174'

X_API_KEY = env('X_API_KEY')
print(X_API_KEY)
# X_API_KEY = os.environ.get('X_API_KEY') # noqa

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Only for development
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS =[
    "http://localhost",
    VERCEL_APP_URL,
    ENNIE_LOCALHOST_1,
    ENNIE_LOCALHOST_2
]



CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

ALLOWED_HOSTS = ['https://9ad2bd0fd479.ngrok-free.app', VERCEL_APP_URL, 'https://e-commerce-project-603j.onrender.com/', 'localhost', '127.0.0.1']
DEBUG = True


CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "x-csrftoken",
    "ngrok-skip-browser-warning",
    "x-api-key"
    # add other headers if needed
]

CORS_ALLOW_CREDENTIALS = True

# Email settings for development
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



INTERNAL_IPS = ['127.0.0.1']

# Debug Toolbar Configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True,
    'INTERCEPT_REDIRECTS': False,
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {module} {thread:d} - {message}', # noqa
            'style': '{',
            'datefmt': '%d-%m-%Y %H:%M:%S'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'e_commerce.log'), # noqa
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.server': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

ENVIRONMENT_VARIABLE = True
POSTGRESS = True

# Database Configuration - FIXED
try:
    # Try to get Supabase database URL first
    DB_SUPABASE_ENGINE = env('DB_SUPABASE_ENGINE', default=None)
    
    if DB_SUPABASE_ENGINE:
        print("Using Supabase database...")
        # Clean and ensure it's a string
        DB_SUPABASE_ENGINE = DB_SUPABASE_ENGINE.strip()
        
        # Ensure it's a string, not bytes
        if isinstance(DB_SUPABASE_ENGINE, bytes):
            DB_SUPABASE_ENGINE = DB_SUPABASE_ENGINE.decode('utf-8')
            
        DATABASES = {
            "default": dj_database_url.parse(DB_SUPABASE_ENGINE)
        }
        print("Supabase database configured successfully")
    else:
        # Fallback to local PostgreSQL
        print("Using local PostgreSQL database...")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'e_commerce',
                'USER': 'postgres',
                'PASSWORD': 'MrNote11',
                'HOST': 'localhost',
                'PORT': '5432',
            }
        }
        
except Exception as e:
    print(f"Database configuration error: {e}")
    print("Falling back to SQLite...")
    # Ultimate fallback to SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Celery Configuration Options
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
CELERY_ACCEPT_CONTENT = ['application/json']


CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Email settings
EMAIL_BACKEND = 'config.email_config.CustomEmailBackend'

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.mailgun.org') # noqa
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587)) # noqa
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER) # noqa
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

EMAIL_SSL_CONTEXT = ssl._create_unverified_context()

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'MAX_CONNECTIONS': 1000,
            'CONNECTION_POOL_KWARGS': {'max_connections': 100},
        }
    }
}

# Cache timeouts
CACHE_TIMEOUT_SHORT = 300  # 5 minutes for frequently changing data
CACHE_TIMEOUT_MEDIUM = 1800  # 30 minutes for moderately changing data
CACHE_TIMEOUT_LONG = 3600  # 1 hour for analytics and rarely changing data
CACHE_TIMEOUT_VERY_LONG = 86400  # 24 hours for static data

# Use Redis for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Payment integration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '') # noqa
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '') # noqa
PAYSTACK_API_URL = 'https://api.paystack.co'

ADMIN_URL = os.environ.get('ADMIN_URL') # noqa
