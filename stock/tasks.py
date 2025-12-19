from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json
import logging
from django.db import transaction
from django.db.models import F
from .models import Product, Cart, Order, OrderItem, CartItem  
from e_commerce.modules.redis_cart import RedisCartService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id, user_email, user_name, order_amount):
    """
    Send order confirmation email
    """
    try:
        subject = f"Order Confirmation - #{order_id}"
        
        message = f"""
Dear {user_name},

Thank you for your order! Your order has been confirmed.

Order ID: {order_id}
Amount: ₦{order_amount:,.2f}
Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}

We will notify you when your order ships.

Best regards,
{'e_commerce Our Store'} Team
"""
        
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False
        )
        
        logger.info(f"Order confirmation email sent to {user_email} for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error sending order confirmation email: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes



@shared_task(bind=True, max_retries=3)
def schedule_payment_expiry_check(self, payment_reference, expiry_seconds):
    """
    Schedule a task to check if payment expired
    """
    try:
        from payment.models import Payment, PaystackTransaction
        
        # Schedule check after expiry time
        from celery import current_app
        current_app.send_task(
            'stock.tasks.check_payment_expiry',
            args=[payment_reference],
            countdown=expiry_seconds
        )
        
        logger.info(f"Scheduled expiry check for payment {payment_reference}")
        
    except Exception as e:
        logger.error(f"Error scheduling expiry check: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=2)
def check_payment_expiry(self, payment_reference):
    """
    Check if payment has expired and update status
    """
    try:
        with transaction.atomic():
            from payment.models import Payment, PaystackTransaction
            
            # Get payment with lock
            payment = Payment.objects.select_for_update().get(
                transaction_reference=payment_reference,
                status='Pending'
            )
            
            # Get transaction with lock
            transaction_obj = PaystackTransaction.objects.select_for_update().get(
                reference=payment_reference,
                status='pending'
            )
            
            # Check if payment was created more than 30 minutes ago
            if timezone.now() - payment.created_at > timedelta(minutes=30):
                payment.status = 'Expired'
                payment.save()
                
                transaction_obj.status = 'expired'
                transaction_obj.save()
                
                # Restore cart status
                if transaction_obj.cart:
                    cart = Cart.objects.select_for_update().get(
                        cart_id=transaction_obj.cart.cart_id
                    )
                    cart.status = Cart.StatusChoice.PENDING
                    cart.save()
                
                logger.info(f"Payment {payment_reference} marked as expired")
                
    except Payment.DoesNotExist:
        logger.warning(f"Payment {payment_reference} not found or already processed")
    except Exception as e:
        logger.error(f"Error checking payment expiry: {e}")


@shared_task
def clean_expired_carts():
    """
    Clean up expired carts from Redis
    """
    try:
        # This task runs periodically to clean up old carts
        # In production, you'd implement a more sophisticated cleanup
        logger.info("Clean expired carts task started")
        
        # Example: Mark abandoned carts older than 3 days
        # You could implement this by scanning cart metadata
        
    except Exception as e:
        logger.error(f"Error cleaning expired carts: {e}")


@shared_task
def send_cart_reminders():
    """
    Send reminders for abandoned carts
    """
    try:
        from home.models import User
        
        # Find carts with last activity > 24 hours
        # This is a simplified implementation
        logger.info("Cart reminders task started")
        
        # In production, you would:
        # 1. Scan Redis for cart metadata
        # 2. Find carts with last_activity > 24 hours
        # 3. Send reminder emails
        
    except Exception as e:
        logger.error(f"Error sending cart reminders: {e}")


@shared_task
def update_product_cache():
    """
    Update product cache periodically
    """
    try:
        # Get popular products
        products = Product.objects.filter(
            stock__gt=0
        ).order_by('-timestamp')[:50]
        
        from vendors.serializers import ProductSerializer
        serializer = ProductSerializer(products, many=True)
        
        # Update cache
        cache.set('popular_products', serializer.data, 3600)
        
        logger.info("Product cache updated")
        
    except Exception as e:
        logger.error(f"Error updating product cache: {e}")


@shared_task
def cleanup_orphaned_carts_task():
    """
    Celery task to periodically clean up orphaned carts
    Schedule this to run every hour or daily
    """
    try:
        cart_service = RedisCartService()
        cleaned_count = cart_service.cleanup_orphaned_carts()
        
        logger.info(f" Periodic cleanup: Cleaned {cleaned_count} orphaned carts")
        return {
            'success': True,
            'cleaned_count': cleaned_count
        }
        
    except Exception as e:
        logger.error(f" Periodic cleanup failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_expired_sessions_and_carts():
    """
    Clean up expired sessions and their associated carts
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from stock.models import Cart
        
        # Get expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        session_count = expired_sessions.count()
        
        # Delete expired sessions (this will cascade to cart cleanup if needed)
        expired_sessions.delete()
        
        logger.info(f" Cleaned up {session_count} expired sessions")
        
        # Also cleanup orphaned carts
        cart_service = RedisCartService()
        cart_count = cart_service.cleanup_orphaned_carts()
        
        logger.info(f" Cleaned up {cart_count} orphaned carts")
        
        return {
            'success': True,
            'sessions_cleaned': session_count,
            'carts_cleaned': cart_count
        }
        
    except Exception as e:
        logger.error(f" Session/cart cleanup failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


# @shared_task(bind=True, max_retries=3)
# def process_order_payment_webhook(self, payment_reference, event_data):
#     """
#     Process payment webhook asynchronously
#     """
#     try:
#         from payment.models import Payment, PaystackTransaction
#         from payment.paystack_service import PaystackService
        
#         # Verify payment with Paystack
#         paystack_service = PaystackService()
#         verification = paystack_service.verify_transaction(payment_reference)
        
#         if verification.get('status'):
#             payment_status = verification['data']['status']
            
#             if payment_status == 'success':
#                 # Update payment and order status
#                 try:
#                     payment = Payment.objects.get(transaction_reference=payment_reference)
#                     payment.status = 'Paid'
#                     payment.paid_at = timezone.now()
#                     payment.metadata = verification['data']
#                     payment.save()
                    
#                     # Update order
#                     if payment.order:
#                         payment.order.status = 'Paid'
#                         payment.order.save()
                        
#                         # Send confirmation email
#                         send_order_confirmation_email.delay(
#                             payment.order.id,
#                             payment.user.email,
#                             payment.user.username,
#                             float(payment.amount)
#                         )
                        
#                 except Payment.DoesNotExist:
#                     logger.warning(f"Payment not found: {payment_reference}")
                    
#         logger.info(f"Processed payment webhook for {payment_reference}")
        
#     except Exception as e:
#         logger.error(f"Error processing payment webhook: {e}")
#         raise self.retry(exc=e, countdown=300)