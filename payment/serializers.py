from rest_framework import serializers
from .models import Payment, PaystackTransaction, PaystackSubscription
from stock.models import Cart, Order


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.paystack_checkout_id', read_only=True, allow_null=True)
    cart_id = serializers.UUIDField(source='cart.cart_id', read_only=True, allow_null=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'order',
            'order_id',
            'cart',
            'cart_id',
            'payment_method',
            'amount',
            'currency',
            'status',
            'transaction_reference',
            'metadata',
            'created_at',
            'updated_at',
            'paid_at'
        ]
        read_only_fields = [
            'transaction_reference',
            'status',
            'created_at',
            'updated_at',
            'paid_at'
        ]


class PaystackTransactionSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(
        source='order.paystack_checkout_id',
        read_only=True,
        allow_null=True
    )
    cart_id = serializers.UUIDField(
        source='cart.cart_id',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = PaystackTransaction
        fields = [
            'id',
            'order',
            'order_id',
            'cart',
            'cart_id',
            'reference',
            'amount',
            'status',
            'authorization_url',
            'access_code',
            'metadata',
            'created_at',
            'updated_at',
            'verified_at'
        ]
        read_only_fields = [
            'reference',
            'status',
            'authorization_url',
            'access_code',
            'created_at',
            'updated_at',
            'verified_at'
        ]

class TransactionSummarySerializer(serializers.Serializer):
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_income = serializers.DecimalField(max_digits=10, decimal_places=2)


class TransactionChartSerializer(serializers.Serializer):
    income_expense_chart = serializers.JSONField()
    category_income_chart = serializers.JSONField()
    category_expense_chart = serializers.JSONField()
    
    
class InitializePaymentFromCartSerializer(serializers.Serializer):
    """Serializer for initializing payment from cart"""
    cart_id = serializers.UUIDField(
        help_text="Cart ID to pay for"
    )
    callback_url = serializers.URLField(
        required=False,
        help_text="URL to redirect after payment (optional)"
    )
    
    def validate_cart_id(self, value):
        """Validate that cart exists and belongs to user"""
        request = self.context.get('request')
        
        try:
            cart = Cart.objects.get(cart_id=value, user=request.user)
            
            # Check if cart has items
            if not cart.cart_items.exists():
                raise serializers.ValidationError("Cart is empty")
            
            # Check if cart is already paid
            if cart.status == Cart.StatusChoice.SUCCESSFUL:
                raise serializers.ValidationError("This cart has already been paid for")
            
            return value
            
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart not found or doesn't belong to you")


class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for verifying payment"""
    reference = serializers.CharField(
        help_text="Paystack transaction reference"
    )


class DirectCardPaymentSerializer(serializers.Serializer):
    """Serializer for direct card payment"""
    cart_id = serializers.UUIDField(
        help_text="Cart ID to pay for"
    )
    card_number = serializers.CharField(
        max_length=19,
        help_text="Card number"
    )
    expiry_month = serializers.CharField(
        max_length=2,
        help_text="Expiry month (MM)"
    )
    expiry_year = serializers.CharField(
        max_length=2,
        help_text="Expiry year (YY)"
    )
    cvv = serializers.CharField(
        max_length=4,
        help_text="CVV"
    )
    pin = serializers.CharField(
        max_length=6,
        help_text="Card PIN"
    )
    
    def validate_cart_id(self, value):
        """Validate that cart exists"""
        request = self.context.get('request')
        
        try:
            cart = Cart.objects.get(cart_id=value, user=request.user)
            
            if not cart.cart_items.exists():
                raise serializers.ValidationError("Cart is empty")
            
            if cart.status == Cart.StatusChoice.SUCCESSFUL:
                raise serializers.ValidationError("This cart has already been paid for")
            
            return value
            
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart not found")


class SubmitOTPSerializer(serializers.Serializer):
    """Serializer for submitting OTP"""
    otp = serializers.CharField(
        max_length=10,
        help_text="One-time password from bank"
    )
    reference = serializers.CharField(
        help_text="Transaction reference"
    )


class PaystackSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Paystack subscriptions (future use)"""
    
    class Meta:
        model = PaystackSubscription
        fields = [
            'id',
            'subscription_code',
            'plan_code',
            'status',
            'amount',
            'interval',
            'next_payment_date',
            'metadata',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'subscription_code',
            'plan_code',
            'status',
            'next_payment_date',
            'created_at',
            'updated_at'
        ]