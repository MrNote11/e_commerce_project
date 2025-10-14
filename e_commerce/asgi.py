"""
WSGI config for e_commerce project.
"""

import os
from django.core.wsgi import get_wsgi_application

# Determine environment
if os.getenv('env', 'dev') == 'prod':
    settings_module = "e_commerce.settings.prod"
else:
    settings_module = "e_commerce.settings.dev"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_wsgi_application()