"""
ASGI config for e_commerce project.
"""

import os
from django.core.asgi import get_asgi_application

# Determine environment
if os.getenv('env', 'dev') == 'prod':
    settings_module = "e_commerce.settings.prod"
else:
    settings_module = "e_commerce.settings.dev"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_asgi_application()