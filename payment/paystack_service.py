import requests
import json
from decimal import Decimal
import logging
from e_commerce.modules.utils import log_request

from .paystack_config import (
    PAYSTACK_SECRET_KEY,
    PAYSTACK_PUBLIC_KEY,
    PAYSTACK_INITIALIZE_URL,
    PAYSTACK_VERIFY_URL,
    PAYSTACK_CHARGE_URL,
    PAYSTACK_SUBSCRIPTION_URL,
    PAYSTACK_INTERVALS,
    MINIMUM_AMOUNT,
    MAXIMUM_AMOUNT,
    PAYSTACK_CHARGE_AUTHORIZATION_URL,
    PAYSTACK_API_URL
)

logger = logging.getLogger(__name__)


class PaystackService:
    """Service for handling Paystack payment operations"""
    
    def __init__(self):
        self.secret_key = PAYSTACK_SECRET_KEY
        self.public_key = PAYSTACK_PUBLIC_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method, url, data=None):
        """Make HTTP request to Paystack API"""
        try:
            log_request(f"Paystack Request: {method} {url} | Data: {data}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            log_request(f"Paystack Response: {response.status_code} | {response.text}")
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Try to get Paystack's error message
            try:
                error_data = response.json()
                message = error_data.get('message', str(e))
                log_request(f"Paystack Error: {message} | {error_data}")
                return {
                    'status': False,
                    'message': message,
                    'paystack_error': error_data
                }
            except Exception:
                log_request(f"Paystack Error: {str(e)}")
                return {'status': False, 'message': str(e)}
                
        except requests.exceptions.RequestException as e:
            log_request(f"Paystack Exception: {str(e)}")
            return {'status': False, 'message': f'Connection error: {str(e)}'}

    def initialize_transaction(self, email, amount, callback_url=None, metadata=None, reference=None):
        """
        Initialize a Paystack transaction
        
        Args:
            email: Customer email
            amount: Amount in kobo (₦1 = 100 kobo)
            callback_url: URL to redirect after payment
            metadata: Additional transaction data
            reference: Optional custom reference
            
        Returns:
            dict: Response from Paystack API
        """
        if not MINIMUM_AMOUNT <= amount <= MAXIMUM_AMOUNT:
            raise ValueError(
                f"Amount must be between ₦{MINIMUM_AMOUNT/100} and "
                f"₦{MAXIMUM_AMOUNT/100}"
            )

        data = {
            'email': email,
            'amount': int(amount),  # Ensure it's an integer
            'metadata': metadata or {}
        }
        
        if callback_url:
            data['callback_url'] = callback_url
            
        if reference:
            data['reference'] = reference

        return self._make_request('POST', PAYSTACK_INITIALIZE_URL, data)

    def verify_transaction(self, reference):
        """
        Verify a transaction's status
        
        Args:
            reference: Transaction reference
            
        Returns:
            dict: Response from Paystack API
        """
        url = f"{PAYSTACK_VERIFY_URL}/{reference}"
        return self._make_request('GET', url)

    def charge_saved_card(self, email, amount, authorization_code, metadata=None):
        """
        Charge a saved card using authorization code
        
        Args:
            email: Customer email
            amount: Amount in kobo (₦1 = 100 kobo)
            authorization_code: Authorization code from previous transaction
            metadata: Additional transaction data
            
        Returns:
            dict: Response from Paystack API
        """
        if not MINIMUM_AMOUNT <= amount <= MAXIMUM_AMOUNT:
            raise ValueError(
                f"Amount must be between ₦{MINIMUM_AMOUNT/100} and "
                f"₦{MAXIMUM_AMOUNT/100}"
            )

        data = {
            'email': email,
            'amount': int(amount),
            'authorization_code': authorization_code,
            'metadata': metadata or {}
        }

        return self._make_request('POST', PAYSTACK_CHARGE_AUTHORIZATION_URL, data)

    def charge_card_directly(self, email, amount, card_number, cvv, expiry_month, 
                           expiry_year, pin):
        """
        Charge a card directly and get authorization code
        This is used for the first transaction with a new card
        
        Args:
            email: Customer email
            amount: Amount in kobo
            card_number: Card number
            cvv: Card CVV
            expiry_month: Card expiry month
            expiry_year: Card expiry year
            pin: Card PIN
            
        Returns:
            dict: Response from Paystack API
        """
        data = {
            'email': email,
            'amount': int(amount),
            'card': {
                'number': card_number,
                'cvv': cvv,
                'expiry_month': str(expiry_month),
                'expiry_year': str(expiry_year)
            },
            'pin': pin
        }

        response = self._make_request('POST', PAYSTACK_CHARGE_URL, data)
        
        # If OTP is required, return the reference
        if response.get('status') and response.get('data', {}).get('status') == 'send_otp':
            return {
                'status': True,
                'requires_otp': True,
                'data': {
                    'status': 'send_otp',
                    'reference': response['data']['reference']
                }
            }
        
        # If charge is successful, return the authorization code
        if response.get('status') and response.get('data', {}).get('status') == 'success':
            return {
                'status': True,
                'requires_otp': False,
                'data': {
                    'status': 'success',
                    'authorization_code': response['data']['authorization']['authorization_code'],
                    'reference': response['data']['reference']
                }
            }
        
        return {
            'status': False,
            'message': response.get('message', 'Card charge failed')
        }

    def submit_otp(self, otp, reference):
        """
        Submit OTP for a pending Paystack charge
        
        Args:
            otp: One-time password
            reference: Transaction reference
            
        Returns:
            dict: Response from Paystack API
        """
        data = {
            'otp': otp,
            'reference': reference
        }
        
        url = f"{PAYSTACK_CHARGE_URL}/submit_otp"
        response = self._make_request('POST', url, data)
        
        # If there's a Paystack error, extract the actual error message
        if not response.get('status') and 'paystack_error' in response:
            error_data = response['paystack_error']
            if isinstance(error_data, dict):
                # Try to get the most specific error message
                error_message = (
                    error_data.get('data', {}).get('message') or
                    error_data.get('message') or
                    'OTP verification failed'
                )
                return {
                    'status': False,
                    'message': error_message
                }
        
        return response

    # Subscription methods (for future use)
    def create_subscription(self, customer_email, plan_code, authorization_code=None):
        """Create a subscription"""
        data = {
            'customer': customer_email,
            'plan': plan_code
        }
        if authorization_code:
            data['authorization'] = authorization_code

        return self._make_request('POST', PAYSTACK_SUBSCRIPTION_URL, data)

    def create_plan(self, name, amount, interval, description=None):
        """
        Create a subscription plan
        
        Args:
            name: Plan name
            amount: Amount in kobo (₦1 = 100 kobo)
            interval: One of 'daily', 'weekly', 'monthly', 'quarterly'
            description: Plan description
            
        Returns:
            dict: Response from Paystack API
        """
        if interval not in PAYSTACK_INTERVALS:
            raise ValueError(
                f"Invalid interval. Must be one of {list(PAYSTACK_INTERVALS.keys())}"
            )

        if not MINIMUM_AMOUNT <= amount <= MAXIMUM_AMOUNT:
            raise ValueError(
                f"Amount must be between ₦{MINIMUM_AMOUNT/100} and "
                f"₦{MAXIMUM_AMOUNT/100}"
            )

        data = {
            'name': name,
            'amount': int(amount),
            'interval': PAYSTACK_INTERVALS[interval],
            'description': description
        }

        return self._make_request('POST', f"{PAYSTACK_API_URL}/plan", data)