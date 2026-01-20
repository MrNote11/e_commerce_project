print('dev.py')

from .base import * # noqa
import ssl  # noqa: E402
import os  # noqa: E402
from .base import env
import sys
import dj_database_url

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")


# SECURITY WARNING: don't run with debug turned on in production!
VERCEL_APP_URL = env('VERCEL_APP_URL')


VERCEL_APP_URL_2 = env('VERCEL_APP_URL_2')
ENNIE_LOCALHOST_1 =  'http://localhost:5173'


ENNIE_LOCALHOST_2 =  'http://localhost:5174'
X_API_KEY = env('X_API_KEY')
# print(X_API_KEY)
# X_API_KEY = os.environ.get('X_API_KEY') # noqa

# CORS settings

# CORS settings for development
# Allow localhost with any port for development flexibility
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
    r"^https://.*\.ngrok-free\.app$",  # Allow any ngrok tunnel
]

# For development, you can temporarily enable this if needed
# CORS_ALLOW_ALL_ORIGINS = True  # Only use this if absolutely necessary

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True 
# include allowed headers


CORS_ALLOWED_ORIGINS =[
    "http://localhost",
    VERCEL_APP_URL,
    VERCEL_APP_URL_2,
    ENNIE_LOCALHOST_1,
    ENNIE_LOCALHOST_2,
    "https://*.ngrok-free.app",
    "https://65829ebee0b2.ngrok-free.app"
]


ALLOWED_HOSTS = [VERCEL_APP_URL, 'e-commerce-project-603j.onrender.com', 'localhost', '127.0.0.1', 'e-commerce-project-603j.onrender.com',
                  'e-commerce-project-603j.onrender.com/', '65829ebee0b2.ngrok-free.app', '*.ngrok-free.app', ENNIE_LOCALHOST_2,  VERCEL_APP_URL_2]

DEBUG = True
TIME_ZONE = "Africa/Lagos"

# CSRF trusted origins for development (to allow ngrok and local testing)
CSRF_TRUSTED_ORIGINS = [
    f"http://{host}" for host in ALLOWED_HOSTS if not host.startswith("http")
] + [
    f"https://{host}" for host in ALLOWED_HOSTS if not host.startswith("http")
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
    'cache-control',
    'pragma',
    "ngrok-skip-browser-warning",
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
        'console':{
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose',
        }
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.server': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

#Email
EMAIL_BACKEND = env('EMAIL_BACKEND')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_USE_TLS = env('EMAIL_USE_TLS')
EMAIL_HOST_USER  = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('EMAIL_HOST_USER')


MS_API_KEY  = env('MS_API_KEY')

ENVIRONMENT_VARIABLE = True
POSTGRESS = True
# Database Configuration - CORRECTED
try:
    # Get the Supabase URL from environment
    supabase_url = env('DB_SUPABASE_ENGINE', default=None)
    
    # print(f"Supabase URL from env: {supabase_url}")
    
    if supabase_url:
        # print(" Configuring Supabase database...")
        # Clean the URL
        supabase_url = str(supabase_url).strip()
        
        # Use dj_database_url to parse the URL
        DATABASES = {
            'default': dj_database_url.parse(supabase_url)
        }
        
        # Add SSL requirement for Supabase
        DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}
        DATABASES['default']['CONN_MAX_AGE'] = 600
        
        # print("Supabase database configured successfully")
        
    else:
        # print("Supabase not available, trying manual Supabase config...")
        
        # Try manual Supabase configuration
        supabase_host = env('SUPABASE_HOST', default=None)
        supabase_password = env('SUPABASE_PASSWORD', default=None)
        
        if supabase_host and supabase_password:
            DATABASES = {
                'default': {
                    'ENGINE': env('ENGINE'),
                    'NAME': env('SUPABASE_DB_NAME', 'NAME'),
                    'USER': env('SUPABASE_USER'),
                    'PASSWORD': supabase_password,
                    'HOST': supabase_host,
                    'PORT': env('SUPABASE_PORT'),
                    'OPTIONS': {
                        'sslmode': 'require',
                        # 'pool_mode': env('PORT_MODE'),
                    },
                }
            }
            # print("Manual Supabase configuration successful")
        else:
            # Fallback to local PostgreSQL
            # print(" Using local PostgreSQL database...")
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': 'e_commerce',
                    'USER': 'postgres',
                    'PASSWORD': 'MrNote11',
                    'HOST': 'localhost',
                    'PORT': '5432',
                }
            }
            print("Local PostgreSQL configured successfully")
            
except Exception as e:
    print(f"Database configuration error: {e}")
    import traceback
    traceback.print_exc()
    print(" Falling back to SQLite...")
    # Ultimate fallback to SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print(" SQLite fallback configured")

# FINAL VERIFICATION - This is crucial!
# print(f" FINAL DATABASES config: {DATABASES}")
# print(f" Database ENGINE: {DATABASES['default'].get('ENGINE', 'MISSING ENGINE!')}")



# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Cache configuration with Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'MAX_CONNECTIONS': 1000,
            'CONNECTION_POOL_KWARGS': {'max_connections': 100},
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
        },
        'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"{REDIS_URL}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }},
        'cart': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"{REDIS_URL}/2",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }},
        'KEY_PREFIX': 'e_commerce_cache',
        'TIMEOUT': 300,  # 5 minutes default timeout
    }
}

# Cache timeouts
CACHE_TIMEOUT_SHORT = 300  # 5 minutes for frequently changing data
CACHE_TIMEOUT_MEDIUM = 1800  # 30 minutes for moderately changing data
CACHE_TIMEOUT_LONG = 3600  # 1 hour for analytics and rarely changing data
CACHE_TIMEOUT_VERY_LONG = 86400  # 24 hours for static data

# Session configuration with Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXTENDED = True


# Cart Settings
CART_SESSION_ID = 'cart'
CART_TIMEOUT = 86400 * 7 


# Email SSL Context
EMAIL_SSL_CONTEXT = ssl._create_unverified_context()

# Payment integration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '') # noqa
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '') # noqa
PAYSTACK_API_URL = 'https://api.paystack.co'

# ADMIN_URL = os.environ.get('ADMIN_URL') # noqa
