from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import hashlib
import hmac
import logging
import uuid
import traceback
from stock.models import Cart, Order, OrderItem, Product
from .models import Payment, PaystackTransaction
from .serializers import (
    PaymentSerializer,
    PaystackTransactionSerializer,
    InitializePaymentFromCartSerializer,
    VerifyPaymentSerializer,
    DirectCardPaymentSerializer,
    SubmitOTPSerializer
)

import json
from decimal import Decimal
from django.db.models import Q, Avg, Sum, Count
from e_commerce.modules.redis_cart import RedisCartService
from .paystack_service import PaystackService
from e_commerce.modules.utils import api_response, incoming_request_checks
from rest_framework import viewsets, generics, status, filters
from datetime import datetime, timedelta
from .filters import PaymentFilter, PaystackTransactionFilter, RevenueAnalyticsFilter
from .charting import generate_dashboard_charts, plot_revenue_over_time, plot_category_revenue, plot_payment_method_distribution, plot_payment_status_distribution, plot_daily_transaction_volume, plot_top_products
from stock.serializers import *
from vendors.permission import *

logger = logging.getLogger(__name__)



class PaystackCallbackView(APIView):
    """
     NEW: Handle Paystack redirect after payment
    This is where users land after paying on Paystack
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Handle Paystack callback redirect"""
        reference = request.GET.get('reference') or request.session.get('paystack_reference')
        
        if not reference:
            return redirect(f"{settings.VERCEL_APP_URL}/payment/failed?error=no_reference")
        
        try:
            # Verify payment with Paystack
            paystack = PaystackService()
            response = paystack.verify_transaction(reference)
            
            if not response.get('status'):
                return redirect(f"{settings.VERCEL_APP_URL}/payment/failed?reference={reference}")
            
            payment_status = response['data']['status']
            
            if payment_status == 'success':
                # Payment successful - webhook will handle the rest
                return redirect(f"{settings.VERCEL_APP_URL}/payment/success?reference={reference}")
            else:
                # Payment failed
                return redirect(f"{settings.VERCEL_APP_URL}/payment/failed?reference={reference}&status={payment_status}")
                
        except Exception as e:
            logger.error(f"Error in callback: {str(e)}")
            return redirect(f"{settings.VERCEL_APP_URL}/payment/failed?error=callback_error")


class PaymentViewSet(APIView):
    """Payment management views"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's payment history"""
        try:
            payments = Payment.objects.filter(user=request.user).order_by('-created_at')
            serializer = PaymentSerializer(payments, many=True)
            
            # Calculate totals
            total_income = payments.filter(status='Paid').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            total_failed = payments.filter(status='Failed').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            pending = payments.filter(status='Pending').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            return Response(
                api_response(
                    message="Payment history retrieved",
                    status=True,
                    data={
                        'payments': serializer.data,
                        'summary': {
                            'total_payments': len(payments),
                            'total_amount': total_income + total_failed + pending,
                            'total_income': total_income,
                            'total_failed': total_failed,
                            'pending': pending,
                            'success_rate': (len(payments.filter(status='Paid')) / len(payments) * 100) if payments else 0
                        }
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error retrieving payment history: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve payment history",
                    status=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InitializePaymentView(APIView):
    """
    Initialize payment for a cart using Paystack
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=InitializePaymentFromCartSerializer,
        responses={
            200: openapi.Response(
                description="Payment initialized successfully",
                schema=PaystackTransactionSerializer
            ),
            400: "Bad Request"
        },
        operation_description="Initialize Paystack payment for a cart"
    )
    def post(self, request):
        """Initialize payment from cart"""
        status_check, data = incoming_request_checks(request)
        if not status_check:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = InitializePaymentFromCartSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        cart_id = serializer.validated_data['cart_id']
        callback_url = serializer.validated_data.get('callback_url')
        
        try:
            # Get cart
            cart = get_object_or_404(Cart, cart_id=cart_id, user=request.user)
            
            # Calculate cart total
            cart_items = cart.cart_items.all()
            cart_total = sum(item.item_subtotal for item in cart_items)
            
            # Convert amount to kobo
            amount_kobo = int(cart_total * 100)
            
            # Initialize Paystack service
            paystack = PaystackService()
            
            # Generate unique reference
            reference = f"CART-{cart_id}-{uuid.uuid4().hex[:8]}"
            
            # Initialize transaction
            response = paystack.initialize_transaction(
                email=request.user.email,
                amount=amount_kobo,
                callback_url=callback_url,
                reference=reference,
                metadata={
                    'cart_id': str(cart_id),
                    'user_id': request.user.id,
                    'customer_name': request.user.username,
                }
            )
            
            if not response.get('status'):
                return Response(
                    api_response(
                        message=response.get('message', 'Failed to initialize payment'),
                        status=False
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create Payment and PaystackTransaction records
            with transaction.atomic():
                payment_obj = Payment.objects.create(
                    cart=cart,
                    user=request.user,
                    payment_method='paystack',
                    amount=cart_total,
                    currency='NGN',
                    transaction_reference=response['data']['reference'],
                    status='Pending',
                    metadata=response['data']
                )
                
                paystack_transaction = PaystackTransaction.objects.create(
                    payment=payment_obj,
                    user=request.user,
                    cart=cart,
                    reference=response['data']['reference'],
                    amount=cart_total,
                    status='pending',
                    authorization_url=response['data'].get('authorization_url'),
                    access_code=response['data'].get('access_code'),
                    metadata=response['data']
                )
            
            return Response(
                api_response(
                    message="Payment initialized successfully",
                    status=True,
                    data={
                        **PaystackTransactionSerializer(paystack_transaction).data,
                        'authorization_url': response['data'].get('authorization_url'),
                        'access_code': response['data'].get('access_code'),
                    }
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error initializing payment: {str(e)}")
            return Response(
                api_response(
                    message=f'Error initializing payment: {str(e)}',
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )


class PaystackWebhookView(APIView):
    """
     FIXED: Handle Paystack webhooks - THIS IS THE PRIMARY VERIFICATION METHOD
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 1. Verify signature
            signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
            if not signature:
                logger.error("Missing Paystack signature")
                return Response({"error": "Missing signature"}, status=400)

            # 2. Compute and verify signature
            secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
            computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()

            if not hmac.compare_digest(signature, computed):
                logger.error("Invalid Paystack signature")
                return Response({"error": "Invalid signature"}, status=400)

            # 3. Parse request data
            try:
                event_data = json.loads(request.body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook payload")
                return Response({"error": "Invalid JSON"}, status=400)

            event = event_data.get("event")
            data = event_data.get("data", {})

            logger.info(f"Webhook received: {event} - {data.get('reference', 'No reference')}")

            # 4. Route event
            if event == "charge.success":
                return self._handle_charge_success(data)
            elif event == "charge.failed":
                return self._handle_charge_failed(data)
            else:
                logger.info(f"Ignoring webhook event: {event}")
                return Response({"status": "ignored"}, status=200)

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error processing webhook"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _handle_charge_success(self, data):
        """ FIXED: Handle successful charge webhook with proper cart deletion"""
        reference = data.get('reference')
        
        if not reference:
            logger.error("No reference in charge.success webhook")
            return Response({"error": "No reference provided"}, status=400)

        try:
            with transaction.atomic():
                # Get transaction with lock
                transaction_obj = PaystackTransaction.objects.select_for_update().get(
                    reference=reference
                )

                # Avoid double-processing
                if transaction_obj.status == 'success':
                    logger.info(f"Transaction {reference} already processed")
                    return Response({"status": "already_processed"}, status=200)

                # 1. Update transaction
                transaction_obj.status = 'success'
                transaction_obj.verified_at = timezone.now()
                transaction_obj.metadata = data
                transaction_obj.save()

                # 2. Update payment
                payment = transaction_obj.payment
                if payment:
                    payment.status = 'Paid'
                    payment.paid_at = timezone.now()
                    payment.save()

                cart = transaction_obj.cart
                order = transaction_obj.order

                if not cart or not order:
                    logger.error(f"Missing cart or order for transaction {reference}")
                    return Response({"error": "Missing cart or order"}, status=400)

                # 3. Update order status
                order.status = 'Paid'
                order.save()

                # 4. Create order items and reduce stock
                for item in cart.cart_items.all():
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                    )

                    # Reduce stock with lock
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    color = item.selected_color

                    if color and color in product.product_colors:
                        current_stock = product.product_colors[color]
                        if current_stock >= item.quantity:
                            product.product_colors[color] = current_stock - item.quantity
                            
                            # Update total stock
                            total_stock = sum(product.product_colors.values())
                            product.stock = total_stock
                            product.save()
                            
                            logger.info(f"Reduced stock for {product.name} ({color}): {current_stock} -> {product.product_colors[color]}")
                        else:
                            logger.warning(
                                f"Insufficient stock for product {product.id}: "
                                f"Available {current_stock}, Requested {item.quantity}"
                            )
                    else:
                        logger.warning(f"Color {color} not found in product {product.id}")

                # 5.  Clear Redis cart using user ID (no request needed)
                try:
                    from django.core.cache import cache
                    user_id = transaction_obj.user.id
                    redis_key = f'cart:user:{user_id}'
                    metadata_key = f'cart:user:{user_id}:metadata'
                    
                    cache.delete(redis_key)
                    cache.delete(metadata_key)
                    
                    logger.info(f"Cleared Redis cart for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to clear Redis cart: {str(e)}")

                # 6.  DELETE CART - This is the critical fix
                if payment:
                    payment.cart = None  # Remove cart reference before deletion
                    payment.save()
                
                # Delete cart items first
                cart.cart_items.all().delete()
                logger.info(f"Deleted cart items for cart {cart.cart_id}")
                
                # Delete the cart
                cart.delete()
                logger.info(f" Successfully deleted cart {cart.cart_id} after payment")

                logger.info(f" Successfully processed payment for reference: {reference}")
                return Response({"status": "success"}, status=200)

        except PaystackTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for reference: {reference}")
            return Response({"error": "Transaction not found"}, status=404)
        except Exception as e:
            logger.error(f"Error processing charge.success: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)

    def _handle_charge_failed(self, data):
        """Handle failed charge webhook"""
        reference = data.get('reference')
        
        if not reference:
            logger.error("No reference in charge.failed webhook")
            return Response({"error": "No reference provided"}, status=400)

        try:
            with transaction.atomic():
                transaction_obj = PaystackTransaction.objects.select_for_update().get(
                    reference=reference
                )
                
                # Only update if not already failed
                if transaction_obj.status != 'failed':
                    transaction_obj.status = 'failed'
                    transaction_obj.verified_at = timezone.now()
                    transaction_obj.metadata = data
                    transaction_obj.save()
                    
                    # Update payment
                    if transaction_obj.payment:
                        transaction_obj.payment.status = 'Failed'
                        transaction_obj.payment.save()
                    
                    #  Reset cart status to allow retry
                    if transaction_obj.cart:
                        transaction_obj.cart.status = Cart.StatusChoice.PENDING
                        transaction_obj.cart.save()
                    
                    logger.info(f"Marked transaction {reference} as failed - cart available for retry")
                
                return Response({"status": "success"}, status=200)
                        
        except PaystackTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for reference: {reference}")
            return Response({"error": "Transaction not found"}, status=404)
        except Exception as e:
            logger.error(f"Error processing charge.failed: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)