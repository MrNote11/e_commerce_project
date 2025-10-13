from .base import *

print('prod.py')

ALLOWED_HOSTS = ['*']
DEBUG = True

ADMINS  = [('Admin', 'aliyahsulaiman3@gmail.com')]




DATABASES = {
    'default': {  'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
 }