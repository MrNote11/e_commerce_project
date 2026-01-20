from django.conf import settings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PAYSTACK_WEBHOOK_SECRET = os.getenv('PAYSTACK_WEBHOOK_SECRET')

# Paystack API URLs
PAYSTACK_API_URL = 'https://api.paystack.co'
PAYSTACK_INITIALIZE_URL = f'{PAYSTACK_API_URL}/transaction/initialize'
PAYSTACK_VERIFY_URL = f'{PAYSTACK_API_URL}/transaction/verify'
PAYSTACK_CHARGE_URL = f'{PAYSTACK_API_URL}/charge'
PAYSTACK_SUBSCRIPTION_URL = f'{PAYSTACK_API_URL}/subscription'
PAYSTACK_CHARGE_AUTHORIZATION_URL = f'{PAYSTACK_API_URL}/transaction/charge_authorization'

# Paystack Plan Intervals (mapped to our frequency choices)
PAYSTACK_INTERVALS = {
    'daily': 'daily',
    'weekly': 'weekly',
    'monthly': 'monthly',
    'quarterly': 'quarterly'
}

# Minimum amount for transactions (in kobo)
MINIMUM_AMOUNT = 10000  # ₦100 in kobo

# Maximum amount for transactions (in kobo)
MAXIMUM_AMOUNT = 1000000000  # ₦10,000,000 in kobo 