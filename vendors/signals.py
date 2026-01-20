"""
Signals for automatic model creation and updates.
This file must be imported in apps.py ready() method.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from home.models import User, UserProfile, UserOTP
from .models import VendorProfile
import logging
import uuid
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from stock.models import Order, Product, Reviews
from payment.models import Payment
from .models import VendorNotification, ProductPerformance


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def notify_vendor_new_order(sender, instance, created, **kwargs):
    """Notify vendor when a new order is placed"""
    if created and instance.status == 'Pending':
        # Get all vendors involved in this order
        vendors = set()
        for item in instance.items.all():
            vendors.add(item.product.vendor)
        
        for vendor in vendors:
            VendorNotification.objects.create(
                vendor=vendor.vendor_profile,
                type='order',
                title='New Order Received',
                message=f'Order #{instance.paystack_checkout_id} has been placed.',
                link=f'/vendor/orders/{instance.id}'
            )


@receiver(post_save, sender=Payment)
def notify_vendor_payment_received(sender, instance, created, **kwargs):
    """Notify vendor when payment is received"""
    if instance.status == 'Paid' and instance.order:
        # Get all vendors involved in this order
        vendors = set()
        for item in instance.order.items.all():
            vendors.add(item.product.vendor)
        
        for vendor in vendors:
            VendorNotification.objects.create(
                vendor=vendor.vendor_profile,
                type='payment',
                title='Payment Received',
                message=f'Payment of ₦{instance.amount} received for order #{instance.order.paystack_checkout_id}',
                link=f'/vendor/orders/{instance.order.id}'
            )


@receiver(post_save, sender=Product)
def notify_vendor_low_stock(sender, instance, **kwargs):
    """Notify vendor when product stock is low"""
    if instance.stock <= 5 and instance.stock > 0:
        # Check if notification already exists for this product today
        from django.utils import timezone
        today = timezone.now().date()
        
        existing = VendorNotification.objects.filter(
            vendor=instance.vendor.vendor_profile,
            type='low_stock',
            message__contains=instance.name,
            created_at__date=today
        ).exists()
        
        if not existing:
            VendorNotification.objects.create(
                vendor=instance.vendor.vendor_profile,
                type='low_stock',
                title='Low Stock Alert',
                message=f'{instance.name} is running low on stock ({instance.stock} remaining)',
                link=f'/vendor/products/{instance.id}'
            )
    
    elif instance.stock == 0:
        # Out of stock notification
        from django.utils import timezone
        today = timezone.now().date()
        
        existing = VendorNotification.objects.filter(
            vendor=instance.vendor.vendor_profile,
            type='out_of_stock',
            message__contains=instance.name,
            created_at__date=today
        ).exists()
        
        if not existing:
            VendorNotification.objects.create(
                vendor=instance.vendor.vendor_profile,
                type='out_of_stock',
                title='Out of Stock',
                message=f'{instance.name} is now out of stock',
                link=f'/vendor/products/{instance.id}'
            )


@receiver(post_save, sender=Reviews)
def notify_vendor_new_review(sender, instance, created, **kwargs):
    """Notify vendor when a new review is posted"""
    if created:
        VendorNotification.objects.create(
            vendor=instance.product.vendor.vendor_profile,
            type='review',
            title='New Review',
            message=f'New {instance.ratings}-star review for {instance.product.name}',
            link=f'/vendor/products/{instance.product.id}/reviews'
        )
        
        # Update product performance
        ProductPerformance.update_for_product(instance.product)

@receiver(post_save, sender=User)
def create_vendor_profile(sender, instance, created, **kwargs):
    if created and instance.role == User.Role.VENDOR:
        if not VendorProfile.objects.filter(user=instance).select_related("user").exists():
            try:
                VendorProfile.objects.create(
                    user=instance,
                    contact_email=instance.email,
                    store_name=f"store_{instance.id}",
                )
            except Exception as e:
                logger.error(f"Failed to create VendorProfile: {e}")