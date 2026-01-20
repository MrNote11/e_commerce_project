# debug_django.py
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings.dev')

# Try to setup Django with minimal apps
try:
    import django
    from django.conf import settings
    
    # Minimal settings for testing
    test_settings = {
        'INSTALLED_APPS': [
            'django.contrib.auth',
            'django.contrib.contenttypes',
        ],
        'DATABASES': settings.DATABASES,
        'SECRET_KEY': settings.SECRET_KEY,
    }
    
    # Temporarily override settings
    for key, value in test_settings.items():
        setattr(settings, key, value)
    
    django.setup()
    print(" Django setup successful with minimal apps")
    
    # Now test each app one by one
    apps_to_test = [
        'home',
        'stock',
        'vendors',
        'payments',
    ]
    
    for app in apps_to_test:
        try:
            print(f"\nTesting {app}...")
            settings.INSTALLED_APPS.append(f'{app}.apps.{app.title()}Config')
            django.setup()
            print(f" {app} works fine")
        except Exception as e:
            print(f" {app} causes error: {e}")
            # Reset
            settings.INSTALLED_APPS.remove(f'{app}.apps.{app.title()}Config')
            
except Exception as e:
    print(f" Error: {e}")
    import traceback
    traceback.print_exc()