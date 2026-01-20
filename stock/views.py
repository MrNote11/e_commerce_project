from django.shortcuts import render
from django.shortcuts import redirect
from e_commerce.modules.utils import incoming_request_checks, api_response, log_request
from e_commerce.modules.exceptions import raise_serializer_error_msg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import HttpResponse
from drf_yasg import openapi
from rest_framework.generics import ListAPIView
from e_commerce.modules.email_utils import send_verification_email, send_welcome_email
from e_commerce.modules.utils import encrypt_text, decrypt_text
from django.utils import timezone
from datetime import timedelta
from e_commerce.modules.throttling import AuthRateThrottle, SignupThrottle
from django.conf import settings
import logging
from decimal import Decimal 
from .models import *
from vendors.models import VendorProfile
from vendors.serializers import CategorySerializer, CategoryListSerializer, ProductSerializer
import json
import uuid
import time
from datetime import datetime
from django.core.cache import cache
from .models import Product, Cart, CartItem
from home.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from stock.filters import ProductFilter
from e_commerce.modules.redis_cart import RedisCartService
from django.db import transaction
from stock.filters import  OrderFilter, CartItemFilter, CategoryFilter, OrderFilter
from payment.models import Payment, PaystackTransaction
from payment.paystack_service import PaystackService
import traceback
from e_commerce.modules.paginations import CustomPagination
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class ProductListViews(APIView, CustomPagination):
    """Product list view with filtering and caching"""
    # permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        
        ProductFilter
    ]
    filterset_class = ProductFilter
    search_fields = ['=name', 'description']
    ordering_fields = ['name', 'price', 'stock']
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        try:
            # Try to get from cache first
            cache_key = 'product_list'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Handle already deserialized data
                if isinstance(cached_data, str):
                    data = json.loads(cached_data)
                else:
                    data = cached_data
                    
                return Response(
                    api_response(
                        message="Products retrieved from cache",
                        status=True,
                        data=data
                    )
                )
            
            # Get products from database
            products = Product.objects.all().select_related('vendor', 'category')
           
            paginated_products = self.paginate_queryset(
                products, request, view=self
            )
            serializer = ProductSerializer(paginated_products, many=True)
            # Cache the result
            if paginated_products is not None:
                return self.get_paginated_response(serializer.data)
            cache.set(cache_key, serializer.data, 60 * 15)
            
            return Response(
                api_response(
                    message="Products retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            )
            
        except Exception as e:
            logger.error(f"Error retrieving products: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve products",
                    status=False,
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductDetailViews(APIView):
    """Product detail view with caching"""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request, pk):
        try:
            cache_key = f'product_detail_{pk}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Handle already deserialized data
                if isinstance(cached_data, str):
                    data = json.loads(cached_data)
                else:
                    data = cached_data
                    
                return Response(
                    api_response(
                        message="Product retrieved from cache",
                        status=True,
                        data=data
                    )
                )
            
            # Get product from database
            product = Product.objects.get(id=pk)
            serializer = ProductSerializer(product)
            
            # Cache the result
            cache.set(cache_key, serializer.data, 60 * 10)
            
            return Response(
                api_response(
                    message="Product retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            )
            
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving product: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve product",
                    status=False,
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartItemView(APIView):
    """Cart item management view"""
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        
    ]
    filterset_class = CartItemFilter
    search_fields = ['=name', 'description']
    ordering_fields = ['name', 'price', 'stock']
    
    def get(self, request, cart_item_id=None):
        """Get user's cart with all items (from Redis cache)"""
        user = request.user
        
        # Initialize Redis cart service
        cart_service = RedisCartService(request=request)
        
        if cart_item_id:
            # Get specific cart item from database
            try:
                cart_item = CartItem.objects.get(id=cart_item_id, cart__user=user)
                serializer = CartItemListSerializer(cart_item)
                return Response(
                    api_response(
                        message="Cart item retrieved successfully",
                        status=True,
                        data=serializer.data
                    )
                )
            except CartItem.DoesNotExist:
                return Response(
                    api_response(
                        message="Cart item not found",
                        status=False,
                        data=None
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get cart summary from Redis
            cart_summary = cart_service.get_cart_summary()
            
            # Also sync with database
            db_cart = cart_service.sync_with_database_cart()
            
            return Response(
                api_response(
                    message="Cart retrieved successfully",
                    status=True,
                    data={
                        'redis_cart': cart_summary,
                        'db_cart': CartSerializer(db_cart).data if db_cart else None
                    }
                )
            )
                
    
    @swagger_auto_schema(
        request_body=CartItemCreateSerializer,
        responses={
            201: "Cart item added successfully",
            400: "Validation failed",
            409: "Concurrency conflict"
        }
    )
    
    def post(self, request):
        """Add items to cart with concurrency control"""
        try:
            logger.info(f"CartItemView.post() called by user: {request.user.id}")
            
            status_check, data = incoming_request_checks(request)
            if not status_check:
                logger.error(f"Request check failed: {data}")
                return Response(
                    api_response(message=data, status=False),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            logger.info(f"Request data: {data}")
            
            # Validate with serializer
            serializer = CartItemCreateSerializer(
                data=data, 
                context={'request': request}
            )
            
            if not serializer.is_valid():
                logger.error(f"Serializer validation failed: {serializer.errors}")
                return Response(
                    api_response(
                        message="Validation failed",
                        status=False,
                        data=serializer.errors
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Serializer validated: {serializer.validated_data}")
            
            with transaction.atomic():
                # Lock the product for update to prevent race conditions
                product_id = serializer.validated_data['product'].id
                selected_size = serializer.validated_data.get('selected_size')
                selected_color = serializer.validated_data.get('selected_color')
                selected_height = serializer.validated_data.get('selected_height')
                quantity = serializer.validated_data.get('quantity', 1)
                
                logger.info(f"Processing product_id: {product_id}, size: {selected_size}, color: {selected_color}, height: {selected_height}, quantity: {quantity}")
                
                # Lock product with select_for_update
                product = Product.objects.select_for_update().get(id=product_id)
                
                # Validate stock with lock
                if selected_color and selected_color in product.product_colors:
                    current_stock = product.product_colors[selected_color]
                    if current_stock < quantity:
                        logger.warning(f"Insufficient stock: {current_stock} < {quantity}")
                        return Response(
                            api_response(
                                message=f"Only {current_stock} items available in {selected_color}",
                                status=False
                            ),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Create database cart item
                cart_item = serializer.save()
                logger.info(f"Database cart item created: {cart_item.id}")
                
                # Also add to Redis cart for faster access
                cart_service = RedisCartService(request=request)
                
                # Check what's currently in Redis BEFORE adding
                redis_cart = cart_service._cache_get(cart_service.redis_key) or {}
                logger.info(f"Redis cart BEFORE adding (keys): {list(redis_cart.keys())}")
                logger.info(f"Redis cart BEFORE adding (full): {redis_cart}")
                
                # Prepare Redis cart item data
                redis_item_data = {
                    'product_id': product.id,
                    'quantity': cart_item.quantity,
                    'price': str(product.price),
                    'name': product.name,
                    'selected_size': cart_item.selected_size,
                    'selected_color': cart_item.selected_color,
                    'selected_height': cart_item.selected_height,
                    'added_at': timezone.now().isoformat()
                }
                
                # Create a unique key
                product_key = f"product_{product.id}"
                if selected_size:
                    product_key += f"_size_{selected_size}"
                if selected_color:
                    product_key += f"_color_{selected_color}"
                if selected_height:
                    product_key += f"_height_{selected_height}"
                
                logger.info(f"Generated Redis key: {product_key}")
                
                # Update or add item
                redis_cart[product_key] = redis_item_data
                
                # Check what's in Redis AFTER adding
                logger.info(f"Redis cart AFTER adding (keys): {list(redis_cart.keys())}")
                
                # Save to Redis
                cart_service._cache_set(cart_service.redis_key, redis_cart)
                
                # Update metadata
                cart_service._update_metadata(
                    items_count=len(redis_cart),
                    total_amount=str(sum(
                        Decimal(item['price']) * item['quantity'] 
                        for item in redis_cart.values()
                    ))
                )
                
                logger.info(f"Redis cart saved. Total items: {len(redis_cart)}")
            
            return Response(
                api_response(
                    message="Item added to cart successfully",
                    status=True,
                    data=CartItemListSerializer(cart_item).data
                ),
                status=status.HTTP_201_CREATED
            )
            
        except Product.DoesNotExist:
            logger.error(f"Product {product_id} does not exist")
            return Response(
                api_response(
                    message="Product not found",
                    status=False
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                api_response(
                    message=f"Failed to add item to cart: {str(e)}",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def delete(self, request, cart_item_id=None):
        """Delete specific cart item or clear entire cart"""
        try:
            if cart_item_id:
                # Delete specific cart item from database
                cart_item = CartItem.objects.get(
                    id=cart_item_id, 
                    cart__user=request.user
                )
                
                # Get the product attributes before deleting
                product_id = cart_item.product.id
                selected_size = cart_item.selected_size
                selected_color = cart_item.selected_color
                selected_height = cart_item.selected_height
                
                # Remove from Redis cart
                cart_service = RedisCartService(request=request)
                redis_cart = cart_service._cache_get(cart_service.redis_key) or {}
                
                #  FIXED: Find the exact Redis key
                redis_key_to_delete = None
                for redis_key, item_data in redis_cart.items():
                    if (item_data.get('product_id') == product_id and
                        item_data.get('selected_size') == selected_size and
                        item_data.get('selected_color') == selected_color and
                        item_data.get('selected_height') == selected_height):
                        redis_key_to_delete = redis_key
                        break
                
                logger.info(f"Deleting cart item: product_id={product_id}, size={selected_size}, color={selected_color}, height={selected_height}")
                logger.info(f"Found Redis key to delete: {redis_key_to_delete}")
                
                if redis_key_to_delete and redis_key_to_delete in redis_cart:
                    del redis_cart[redis_key_to_delete]
                    cart_service._cache_set(cart_service.redis_key, redis_cart)
                    
                    #  FIXED: Update metadata with correct total
                    if redis_cart:  # If cart not empty
                        total_amount = sum(
                            Decimal(item['price']) * item['quantity'] 
                            for item in redis_cart.values()
                        )
                        cart_service._update_metadata(
                            items_count=len(redis_cart),
                            total_amount=str(total_amount)
                        )
                    else:  # If cart is now empty
                        cart_service._update_metadata(
                            items_count=0,
                            total_amount='0.00'
                        )
                
                # Delete from database
                cart_item.delete()
                
                message = "Item removed from cart successfully"
            else:
                # Clear entire cart
                cart = Cart.objects.get(user=request.user)
                cart.cart_items.all().delete()
                
                # Clear Redis cart
                cart_service = RedisCartService(request=request)
                cart_service.clear_cart()
                
                message = "Cart cleared successfully"
            
            return Response(
                api_response(
                    message=message,
                    status=True,
                    data=None
                )
            )
            
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                api_response(
                    message="Cart or item not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting from cart: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                api_response(
                    message=f"Error: {str(e)}",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
            
            
    @swagger_auto_schema(
        request_body=CartItemCreateSerializer,
        responses={
            200: "Cart item updated successfully",
            400: "Validation failed",
            404: "Cart item not found"
        }
    )
    def patch(self, request, cart_item_id):
        """Update cart item quantity with concurrency control"""
        try:
            status_check, data = incoming_request_checks(request)
            if not status_check:
                return Response(
                    api_response(message=data, status=False),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            with transaction.atomic():
                # Lock cart item and product for update
                cart_item = CartItem.objects.select_for_update().get(
                    id=cart_item_id, 
                    cart__user=request.user
                )
                
                # Lock the product
                product = Product.objects.select_for_update().get(
                    id=cart_item.product.id
                )
                
                serializer = CartItemCreateSerializer(
                    cart_item, 
                    data=data, 
                    partial=True, 
                    context={'request': request}
                )
                
                if not serializer.is_valid():
                    return Response(
                        api_response(
                            message="Validation failed",
                            status=False,
                            data=serializer.errors
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate stock with lock
                selected_color = serializer.validated_data.get(
                    'selected_color', 
                    cart_item.selected_color
                )
                quantity = serializer.validated_data.get(
                    'quantity', 
                    cart_item.quantity
                )
                
                if selected_color and selected_color in product.product_colors:
                    current_stock = product.product_colors[selected_color]
                    if current_stock < quantity:
                        logger.warning(f"Insufficient stock: {current_stock} < {quantity}")
                        return Response(
                            api_response(
                                message=f"Only {current_stock} items available in {selected_color}",
                                status=False
                            ),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Save the updated cart item
                updated_cart_item = serializer.save()
                
                #  FIXED: Update Redis cart with the correct key
                cart_service = RedisCartService(request=request)
                redis_cart = cart_service._cache_get(cart_service.redis_key) or {}
                
                # Find the exact Redis key that matches this cart item
                redis_key_to_update = None
                for redis_key, item_data in redis_cart.items():
                    if (item_data.get('product_id') == updated_cart_item.product.id and
                        item_data.get('selected_size') == updated_cart_item.selected_size and
                        item_data.get('selected_color') == updated_cart_item.selected_color and
                        item_data.get('selected_height') == updated_cart_item.selected_height):
                        redis_key_to_update = redis_key
                        break
                
                # If found, update the Redis cart
                if redis_key_to_update and redis_key_to_update in redis_cart:
                    redis_cart[redis_key_to_update]['quantity'] = updated_cart_item.quantity
                    redis_cart[redis_key_to_update]['price'] = str(updated_cart_item.product.price)
                    cart_service._cache_set(cart_service.redis_key, redis_cart)
                    
                    #  FIXED: Update metadata with correct total
                    total_amount = sum(
                        Decimal(item['price']) * item['quantity'] 
                        for item in redis_cart.values()
                    )
                    
                    cart_service._update_metadata(
                        items_count=len(redis_cart),
                        total_amount=str(total_amount)
                    )
                    
                    logger.info(f"Redis cart updated for key: {redis_key_to_update}, new quantity: {updated_cart_item.quantity}")
                else:
                    # If Redis key not found, add it
                    logger.warning(f"Redis key not found for cart item {updated_cart_item.id}, adding new entry")
                    
                    # Create unique Redis key
                    product_key = f"product_{updated_cart_item.product.id}"
                    if updated_cart_item.selected_size:
                        product_key += f"_size_{updated_cart_item.selected_size}"
                    if updated_cart_item.selected_color:
                        product_key += f"_color_{updated_cart_item.selected_color}"
                    if updated_cart_item.selected_height:
                        product_key += f"_height_{updated_cart_item.selected_height}"
                    
                    # Add to Redis cart
                    redis_cart[product_key] = {
                        'product_id': updated_cart_item.product.id,
                        'quantity': updated_cart_item.quantity,
                        'price': str(updated_cart_item.product.price),
                        'name': updated_cart_item.product.name,
                        'selected_size': updated_cart_item.selected_size,
                        'selected_color': updated_cart_item.selected_color,
                        'selected_height': updated_cart_item.selected_height,
                        'added_at': timezone.now().isoformat()
                    }
                    
                    cart_service._cache_set(cart_service.redis_key, redis_cart)
                    
                    # Update metadata
                    total_amount = sum(
                        Decimal(item['price']) * item['quantity'] 
                        for item in redis_cart.values()
                    )
                    
                    cart_service._update_metadata(
                        items_count=len(redis_cart),
                        total_amount=str(total_amount)
                    )
            
            return Response(
                api_response(
                    message="Cart updated successfully",
                    status=True,
                    data=CartItemListSerializer(updated_cart_item).data
                )
            )
                
        except CartItem.DoesNotExist:
            return Response(
                api_response(
                    message="Cart item not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating cart: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                api_response(
                    message=f"Error updating cart: {str(e)}",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )



class CartCheckoutAPIView(APIView):
    """
     FIXED: Initialize payment WITHOUT deleting cart
    Cart will be deleted only after successful payment verification
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process cart checkout - Initialize payment only"""
        try:
            status_check, data = incoming_request_checks(request)
            if not status_check:
                return Response(
                    api_response(message=data, status=False),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            with transaction.atomic():
                cart_id = data.get('cart_id')
                cart = Cart.objects.select_for_update().get(
                    cart_id=cart_id, 
                    user=request.user
                )
                
                # Check if cart has items
                if not cart.cart_items.exists():
                    return Response(
                        api_response(
                            message="Cart is empty",
                            status=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if cart is already being processed
                if cart.status == Cart.StatusChoice.PROCESSING:
                    return Response(
                        api_response(
                            message="This cart is already being processed",
                            status=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculate total
                cart_total = sum(
                    item.item_subtotal for item in cart.cart_items.all()
                )
                
                # MARK CART AS PROCESSING (prevents duplicate checkouts)
                cart.status = Cart.StatusChoice.PROCESSING
                cart.save() 
                
                # Initialize Paystack payment
                paystack_service = PaystackService()
                
                # Generate unique reference
                paystack_reference = f"ORDER-{uuid.uuid4().hex[:8]}-{int(timezone.now().timestamp())}"
                
                #  FIXED: Proper callback URLs
                base_url = request.build_absolute_uri('/').rstrip('/')
                callback_url = f"{base_url}/callback/"  # Generic callback
                print(f"Callback URL: {callback_url}")
                # Initialize Paystack payment
                response = paystack_service.initialize_transaction(
                    email=request.user.email,
                    amount=int(cart_total * 100),  # Convert to kobo
                    callback_url=callback_url,
                    metadata={
                        'cart_id': str(cart_id),
                        'user_id': request.user.id,
                        'reference': paystack_reference,
                    }
                )
                
                if response.get('status'):
                    # Create an order record (marked as pending)
                    order = Order.objects.create(
                        paystack_checkout_id=paystack_reference,
                        amount=cart_total,
                        currency='NGN',
                        user=request.user,
                        status='Pending'
                    )
                    
                    # Create payment record
                    payment = Payment.objects.create(
                        order=order,
                        cart=cart,
                        user=request.user,
                        payment_method='paystack',
                        amount=cart_total,
                        currency='NGN',
                        transaction_reference=response['data']['reference'],
                        status='Pending',
                        metadata=response['data']
                    )
                    
                    # Create Paystack transaction record
                    PaystackTransaction.objects.create(
                        payment=payment,
                        user=request.user,
                        cart=cart,
                        order=order,
                        reference=response['data']['reference'],
                        amount=cart_total,
                        status='pending',
                        authorization_url=response['data'].get('authorization_url'),
                        access_code=response['data'].get('access_code'),
                        metadata=response['data']
                    )
                    
                    #  Store reference in session for callback handling
                    request.session['paystack_reference'] = response['data']['reference']
                    request.session['cart_id'] = str(cart_id)
                    request.session.modified = True
                    
                    #  DO NOT DELETE CART HERE - Wait for payment verification
                    #  DO NOT REDUCE STOCK HERE - Wait for payment verification
                    #  DO NOT CLEAR REDIS CART HERE - Wait for payment verification
                    
                    return Response(
                        api_response(
                            message="Payment initialized. Please complete payment.",
                            status=True,
                            data={
                                'order_id': order.id,
                                'order_reference': order.paystack_checkout_id,
                                'payment_reference': response['data']['reference'],
                                'authorization_url': response['data'].get('authorization_url'),
                                'access_code': response['data'].get('access_code'),
                                'amount': float(cart_total),
                                'currency': 'NGN',
                                'payment_status': 'pending',
                            }
                        )
                    )
                else:
                    # Reset cart status if payment initialization fails
                    cart.status = Cart.StatusChoice.PENDING
                    cart.save()
                    
                    return Response(
                        api_response(
                            message=f"Payment initialization failed: {response.get('message', 'Unknown error')}",
                            status=False
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
        except Cart.DoesNotExist:
            return Response(
                api_response(
                    message="Cart not found",
                    status=False
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Reset cart status if exists
            try:
                if 'cart' in locals():
                    cart.status = Cart.StatusChoice.PENDING
                    cart.save()
            except:
                pass
                
            return Response(
                api_response(
                    message=f"Checkout failed: {str(e)}",
                    status=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartCountAPIView(APIView):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
  
    ]
    
    search_fields = ['=name', 'description']
    ordering_fields = ['name', 'price', 'stock']
    
    """Get cart item count from Redis"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            cart_service = RedisCartService(request=request)
            count = cart_service.get_item_count()
            
            return Response(
                api_response(
                    message="Cart count retrieved",
                    status=True,
                    data={'count': count}
                )
            )
        except Exception as e:
            logger.error(f"Error getting cart count: {str(e)}")
            return Response(
                api_response(
                    message=f"Error getting cart count: {str(e)}",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )


class CategoryListViews(APIView, CustomPagination):
    """Category list view"""
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        
    ]
    filterset_class = CategoryFilter
    search_fields = ['=name', 'description']
    ordering_fields = ['name', 'price', 'stock']
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            categories = Category.objects.all()
            paginated_categories = self.paginate_queryset(categories, request, view=self)
            serializer = CategoryListSerializer(paginated_categories, many=True)
            if paginated_categories is not None:
                return self.get_paginated_response(serializer.data)
            return Response(
                api_response(
                    message="Categories retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            )
        except Exception as e:
            logger.error(f"Error retrieving categories: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve categories",
                    status=False,
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryDetailViews(APIView):
    """Category detail view"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        try:
            category = Category.objects.get(slug=slug)
            serializer = CategorySerializer(category)
            return Response(
                api_response(
                    message="Category retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            ) 
        except Category.DoesNotExist:
            return Response(
                api_response(
                    message="Category not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving category: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve category",
                    status=False,
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ... Rest of your views with similar fixes ...

class OrderAPIView(APIView, CustomPagination):
    """Order management API"""
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        
    ]
    filterset_class = OrderFilter
    search_fields = ['=paystack_checkout_id', 'status']
    ordering_fields = ['created_at', 'amount']
    def get(self, request):
        """Get user's orders"""
        try:
            orders = Order.objects.filter(
                user=request.user
            ).order_by('-created_at')

            paginated_orders = self.paginate_queryset(orders, request, view=self)
            orders_data = []
            for order in paginated_orders:
                orders_data.append({
                    'id': order.id,
                    'order_reference': order.paystack_checkout_id ,
                    'amount': float(order.amount),
                    'currency': order.currency,
                    'status': order.status,
                    'created_at': order.created_at,
                    'item_count': order.items.count()
                })
            if paginated_orders is not None:
                return self.get_paginated_response(orders_data)
            
            return Response(
                api_response(
                    message="Orders retrieved successfully",
                    status=True,
                    data=orders_data
                )
            )
        except Exception as e:
            logger.error(f"Error retrieving orders: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve orders",
                    status=False,
                    data=None
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReviewViewSet(APIView, CustomPagination):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        """Get all reviews for products"""
        reviews = Reviews.objects.all().select_related('product', 'user')
        paginated_reviews = self.paginate_queryset(reviews, request, view=self)
        serializer = ReviewSerializer(paginated_reviews, many=True)
        if paginated_reviews is not None:
            return self.get_paginated_response(serializer.data)
        return Response(
            api_response(
                message="Reviews retrieved successfully",
                status=True,
                data=serializer.data
            )
        )
         
    def post(self, request, *args, **kwargs):

        """Add items to cart or create cart"""
        status_check, data = incoming_request_checks(request)
        if not status_check:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # product_id = data.get("product_id")
        # ratings = data.get("ratings")
        # review_texts = data.get("reviews")

        # product = Product.objects.get(id=product_id)
        # user = User.objects.get(id=request.user.id)

       
        # if Reviews.objects.filter(product=product, user=user).exists():
        #     return Response({"error": "You already dropped a review for this product"}, status=400)
        

        # review  = Reviews.objects.create()
        serializer = ReviewSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                api_response(
                    message="Review created successfully",
                    status=True,
                    data=serializer.data
                )
            )
        else:
            return Response(
                api_response(
                    message="Failed to create review",
                    status=False,
                    data=serializer.errors
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request, pk):
        status_check, data = incoming_request_checks(request)
        if not status_check:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        review = Reviews.objects.get(id=pk)
        if not review:
            return Response(
                api_response(
                    message="Review not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        if not Reviews.objects.filter(id=pk, user=request.user, product=data["product_id"]).exists():
            return Response(
                api_response(
                    message="You have not reviewed this product before",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReviewSerializer(review, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                api_response(
                    message="Review updated successfully",
                    status=True,
                    data=serializer.data
                )
            )
        else:
            return Response(
                api_response(
                    message="Failed to update review",
                    status=False,
                    data=serializer.errors
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, pk):
        try:
            if pk:
                review = Reviews.objects.get(id=pk) 
                review.delete()

                return Response(
                    api_response(
                        message="Review deleted successfully",
                        status=True,
                        data=None
                    ),
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    api_response(
                        message="Review not found",
                        status=False,
                        data=None
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
        except (Reviews.DoesNotExist):
            return Response(
                api_response(
                    message="Review not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )


class WishlistViewSet(APIView, CustomPagination):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        status_check, data = incoming_request_checks(request)
        if not status_check:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        product_id = data.get("product_id")

        user = User.objects.get(id=request.user.id)
        product = Product.objects.get(id=product_id)

        wishlist = Wishlist.objects.filter(user=user, product=product)
        if wishlist:
            wishlist.delete()
            return Response(
                api_response(
                    message="Wishlist deleted successfully",
                    status=True,
                    data=None
                ),
                status=status.HTTP_204_NO_CONTENT
            )

        new_wishlist = Wishlist.objects.create(user=user, product=product)
        serializer = WishlistSerializer(new_wishlist)
        return Response(
            api_response(
                message="Wishlist created successfully",
                status=True,
                data=serializer.data
            )
        )

    def get(self, request):
        user = User.objects.get(id=request.user.id)
        wishlist_items = Wishlist.objects.filter(user=user).select_related('product')
        paginated_wishlist = self.paginate_queryset(wishlist_items, request, view=self)
        serializer = WishlistSerializer(paginated_wishlist, many=True)

        if paginated_wishlist is not None:
            return self.get_paginated_response(serializer.data)

        return Response(
            api_response(
                message="Wishlist retrieved successfully",
                status=True,
                data=serializer.data
            )
        )


class SearchProductsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("query") 
        if not query:
            return Response("No query provided", status=400)

        products = Product.objects.filter(Q(name__icontains=query) | 
                                        Q(description__icontains=query) |
                                        Q(category__name__icontains=query) |
                                        Q(category__choice__icontains=query) |
                                        Q(price__icontains=query) |
                                        Q(product_sizes__icontains=query) |
                                        Q(product_colors__icontains=query)
    )
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
        

class ProductRatingViews(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            product_rating = ProductRating.objects.get(product=product)
    
            data = {
                "product_id": product.id,
                "average_rating": product_rating.average_rating,
                "total_reviews": product_rating.total_reviews,
            }
            return Response(
                api_response(
                    message="Product rating retrieved successfully",
                    status=True,
                    data=data
                )
            )
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except ProductRating.DoesNotExist:
            return Response(
                api_response(
                    message="Product rating not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
            


class OrderDetailAPIView(APIView):
    """Order detail API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        """Get order details"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            
            order_data = {
                'id': order.id,
                'order_reference': order.paystack_checkout_id ,
                'amount': float(order.amount),
                'currency': order.currency,
                'status': order.status,
                'created_at': order.created_at,
                'items': []
            }
            
            for item in order.items.all():
                order_data['items'].append({
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': float(item.product.price),
                    'total': float(item.quantity * item.product.price)
                })
            
            # Check payment status
            try:
                from payment.models import Payment
                payment = Payment.objects.get(order=order)
                order_data['payment'] = {
                    'status': payment.status,
                    'method': payment.payment_method,
                    'reference': payment.transaction_reference,
                    'paid_at': payment.paid_at
                }
            except Payment.DoesNotExist:
                order_data['payment'] = None
            
            return Response(
                api_response(
                    message="Order details retrieved successfully",
                    status=True,
                    data=order_data
                )
            )
            
        except Order.DoesNotExist:
            return Response(
                api_response(
                    message="Order not found",
                    status=False
                ),
                status=status.HTTP_404_NOT_FOUND
            )
            

class CartDebugAPIView(APIView):
    """Debug endpoint to see raw cart data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get raw Redis cart data for debugging"""
        try:
            cart_service = RedisCartService(request=request)
            
            # Get raw Redis data
            redis_cart_raw = cache.get(cart_service.redis_key)
            redis_metadata_raw = cache.get(cart_service.metadata_key)
            
            # Parse if needed
            redis_cart = redis_cart_raw
            if isinstance(redis_cart_raw, str):
                try:
                    redis_cart = json.loads(redis_cart_raw)
                except:
                    pass
            
            redis_metadata = redis_metadata_raw
            if isinstance(redis_metadata_raw, str):
                try:
                    redis_metadata = json.loads(redis_metadata_raw)
                except:
                    pass
            
            # Get database cart
            db_cart = None
            try:
                db_cart = Cart.objects.get(user=request.user)
                db_items = list(CartItem.objects.filter(cart=db_cart).values())
            except Cart.DoesNotExist:
                db_items = []
            
            return Response(
                api_response(
                    message="Debug cart data",
                    status=True,
                    data={
                        'redis_key': cart_service.redis_key,
                        'redis_cart_raw': redis_cart_raw,
                        'redis_cart_parsed': redis_cart,
                        'redis_metadata_raw': redis_metadata_raw,
                        'redis_metadata_parsed': redis_metadata,
                        'database_cart': {
                            'cart_exists': db_cart is not None,
                            'items': db_items,
                            'item_count': len(db_items) if db_items else 0
                        }
                    }
                )
            )
        except Exception as e:
            logger.error(f"Cart debug error: {e}")
            return Response(
                api_response(
                    message=f"Debug error: {str(e)}",
                    status=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Clear Redis cache for debugging"""
        try:
            cart_service = RedisCartService(request=request)
            
            # Clear Redis
            cache.delete(cart_service.redis_key)
            cache.delete(cart_service.metadata_key)
            
            # Clear database cart
            CartItem.objects.filter(cart__user=request.user).delete()
            
            return Response(
                api_response(
                    message="Cart cleared for debugging",
                    status=True,
                    data=None
                )
            )
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return Response(
                api_response(
                    message=f"Error: {str(e)}",
                    status=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class CartHealthCheckView(APIView):
    """
     NEW: Check cart health and sync Redis/DB
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check if Redis and Database carts are in sync"""
        try:
            from stock.models import Cart
            
            cart_service = RedisCartService(request=request)
            
            # Get Redis cart
            redis_cart = cart_service._cache_get(cart_service.redis_key) or {}
            redis_count = len(redis_cart)
            
            # Get DB cart
            db_cart = Cart.objects.filter(user=request.user).first()
            db_count = db_cart.cart_items.count() if db_cart else 0
            
            # Check if they match
            in_sync = redis_count == db_count
            
            response_data = {
                'redis_items': redis_count,
                'database_items': db_count,
                'in_sync': in_sync,
                'redis_key': cart_service.redis_key,
                'status': 'healthy' if in_sync else 'out_of_sync'
            }
            
            if not in_sync:
                logger.warning(
                    f"Cart out of sync for user {request.user.id}: "
                    f"Redis={redis_count}, DB={db_count}"
                )
                
                # Trigger sync
                cart_service.sync_with_database_cart()
                response_data['sync_triggered'] = True
            
            return Response(
                api_response(
                    message="Cart health check completed",
                    status=True,
                    data=response_data
                )
            )
            
        except Exception as e:
            logger.error(f" Error in cart health check: {str(e)}")
            return Response(
                api_response(
                    message=f"Health check failed: {str(e)}",
                    status=False
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
      