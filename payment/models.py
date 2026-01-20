from django.db import models
from home.models import User
from stock.models import Order, Cart
from django.utils import timezone


class Payment(models.Model):
    """
    Generic payment model for tracking all payments
    """
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash on Delivery'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Cancelled', 'Cancelled'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_record',
        null=True,
        blank=True
    )
    cart = models.ForeignKey(
        Cart,
        on_delete=models.SET_NULL,
        related_name='payment_records',
        null=True,
        blank=True,
        help_text="Associated cart for this payment"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_payments'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='paystack'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in Naira"
    )
    currency = models.CharField(
        max_length=10,
        default='NGN',
        help_text="Payment currency"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )
    transaction_reference = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique payment reference"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payment data"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_reference} - {self.user.email}"


class PaystackTransaction(models.Model):
    """
    Tracks Paystack-specific transactions
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='paystack_details',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paystack_user_transactions'
    )
    cart = models.ForeignKey(
        Cart,
        on_delete=models.SET_NULL,
        related_name='paystack_cart_transactions',
        null=True,
        blank=True
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        related_name='paystack_order_transactions',
        null=True,
        blank=True
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        help_text="Paystack transaction reference"
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Transaction amount in Naira"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    authorization_url = models.URLField(
        blank=True,
        null=True,
        help_text="Paystack payment authorization URL"
    )
    access_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Paystack access code"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional transaction data"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Paystack Transaction {self.reference} - {self.user.email}"


class PaystackSubscription(models.Model):
    """
    Tracks Paystack subscriptions (for future use)
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paystack_user_subscriptions'
    )
    subscription_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Paystack subscription code"
    )
    plan_code = models.CharField(
        max_length=100,
        help_text="Paystack plan code"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Subscription amount in Naira"
    )
    interval = models.CharField(
        max_length=20,
        help_text="Subscription interval (daily/weekly/monthly/quarterly)"
    )
    next_payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next payment date"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional subscription data"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['subscription_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.email}'s subscription - {self.subscription_code}"