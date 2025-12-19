# e_commerce/modules/redis_cart.py - IMPROVED VERSION
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from stock.models import Product, Cart, CartItem
from home.models import User
import logging

logger = logging.getLogger(__name__)

class RedisCartService:
    """
    Redis-based shopping cart service with automatic cleanup and DB sync
    """
    
    CART_PREFIX = 'cart:'
    CART_TTL = 7 * 24 * 60 * 60  # 7 days
    ABANDONED_CART_TTL = 3 * 24 * 60 * 60  # 3 days for abandoned carts
    
    def __init__(self, request=None, user=None, cart_key=None):
        self.request = request
        self.user = user or (request.user if request and hasattr(request, 'user') else None)
        
        # Generate or get cart key
        if cart_key:
            self.cart_key = cart_key
        elif request and 'cart_key' in request.session:
            self.cart_key = request.session['cart_key']
        elif self.user and self.user.is_authenticated:
            self.cart_key = f"user_{self.user.id}"
        else:
            self.cart_key = f"anon_{uuid.uuid4().hex}"
            if request:
                request.session['cart_key'] = self.cart_key
        
        self.redis_key = f"{self.CART_PREFIX}{self.cart_key}"
        self.metadata_key = f"{self.redis_key}:metadata"
        
        # Initialize cart metadata
        self._initialize_metadata()
    
    def _initialize_metadata(self):
        """Initialize cart metadata if not exists"""
        metadata = self._cache_get(self.metadata_key)
        
        if not metadata:
            metadata = {
                'created_at': timezone.now().isoformat(),
                'updated_at': timezone.now().isoformat(),
                'user_id': self.user.id if self.user and self.user.is_authenticated else None,
                'user_email': self.user.email if self.user and self.user.is_authenticated else None,
                'is_authenticated': self.user and self.user.is_authenticated,
                'session_count': 1,
                'abandoned': False,
                'checkout_started': False,
                'last_activity': timezone.now().isoformat(),
                'items_count': 0,
                'total_amount': '0.00',
                'status': 'active'
            }
            self._cache_set(self.metadata_key, metadata, timeout=self.CART_TTL)
        else:
            metadata['session_count'] = metadata.get('session_count', 0) + 1
            metadata['last_activity'] = timezone.now().isoformat()
            metadata['status'] = 'active'
            self._cache_set(self.metadata_key, metadata, timeout=self.CART_TTL)
    
    def _cache_get(self, key):
        """Get data from Redis cache with proper JSON handling"""
        try:
            data = cache.get(key)
            if data is None:
                return None
                
            # If data is already a dict/list, return it
            if isinstance(data, (dict, list)):
                return data
                
            # If it's a string, try to parse it as JSON
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data
                    
            return data
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None
    
    def _cache_set(self, key, value, timeout=None):
        """Set data in Redis cache with JSON encoding"""
        try:
            if timeout is None:
                timeout = self.CART_TTL
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            return cache.set(key, value, timeout=timeout)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def _update_metadata(self, **kwargs):
        """Update cart metadata"""
        metadata = self._cache_get(self.metadata_key) or {}
        metadata.update(kwargs)
        metadata['updated_at'] = timezone.now().isoformat()
        metadata['last_activity'] = timezone.now().isoformat()
        self._cache_set(self.metadata_key, metadata)
        return metadata
    
    #  NEW: Check if Redis is available and load from DB if needed
    def _ensure_redis_db_sync(self):
        """
        Ensure Redis and Database are in sync
        If Redis is empty but DB has items, load from DB to Redis
        """
        if not self.user or not self.user.is_authenticated:
            return
        
        try:
            redis_cart_data = self._cache_get(self.redis_key)
            
            # If Redis is empty, check database
            if not redis_cart_data:
                cart = Cart.objects.filter(user=self.user).first()
                
                if cart and cart.cart_items.exists():
                    logger.warning(f"Redis empty but DB has cart for user {self.user.id}. Loading from DB...")
                    
                    # Rebuild Redis from database
                    redis_cart_data = {}
                    
                    for cart_item in cart.cart_items.all():
                        # Create unique key for variant
                        product_key = f"product_{cart_item.product.id}"
                        if cart_item.selected_size:
                            product_key += f"_size_{cart_item.selected_size}"
                        if cart_item.selected_color:
                            product_key += f"_color_{cart_item.selected_color}"
                        if cart_item.selected_height:
                            product_key += f"_height_{cart_item.selected_height}"
                        
                        redis_cart_data[product_key] = {
                            'product_id': cart_item.product.id,
                            'quantity': cart_item.quantity,
                            'price': str(cart_item.product.price),
                            'name': cart_item.product.name,
                            'selected_size': cart_item.selected_size,
                            'selected_color': cart_item.selected_color,
                            'selected_height': cart_item.selected_height,
                            'added_at': cart_item.created_at.isoformat()
                        }
                    
                    # Save to Redis
                    self._cache_set(self.redis_key, redis_cart_data)
                    
                    # Update metadata
                    total_amount = sum(
                        Decimal(item['price']) * item['quantity']
                        for item in redis_cart_data.values()
                    )
                    
                    self._update_metadata(
                        items_count=len(redis_cart_data),
                        total_amount=str(total_amount),
                        status='active',
                        restored_from_db=True,
                        restored_at=timezone.now().isoformat()
                    )
                    
                    logger.info(f" Restored {len(redis_cart_data)} items from DB to Redis for user {self.user.id}")
                    
        except Exception as e:
            logger.error(f"Error in _ensure_redis_db_sync: {str(e)}")
    
    def get_cart_summary(self):
        """Get cart summary with proper empty cart handling and DB sync"""
        logger.info(f"get_cart_summary called for key: {self.redis_key}")
        
        #  NEW: Ensure Redis and DB are in sync first
        self._ensure_redis_db_sync()
        
        redis_cart_data = self._cache_get(self.redis_key) or {}
        metadata = self._cache_get(self.metadata_key) or {}
        
        # Check if cart is empty
        if not redis_cart_data:
            #  NEW: Also check database and clean if needed
            if self.user and self.user.is_authenticated:
                cart = Cart.objects.filter(user=self.user).first()
                if cart and cart.cart_items.exists():
                    logger.warning(f"Redis empty but DB has cart. Cleaning DB cart for user {self.user.id}")
                    cart.cart_items.all().delete()
                    cart.delete()
            
            # Mark cart as empty in metadata
            metadata['items_count'] = 0
            metadata['total_amount'] = '0.00'
            metadata['status'] = 'empty'
            self._cache_set(self.metadata_key, metadata)
            
            logger.info(f"Cart is empty for key: {self.redis_key}")
            
            return {
                'cart_key': self.cart_key,
                'items': [],
                'summary': {
                    'subtotal': 0.00,
                    'total_items': 0,
                    'item_count': 0,
                    'estimated_tax': 0.00,
                    'shipping': 0.00,
                    'total': 0.00
                },
                'metadata': metadata,
                'is_authenticated': self.user and self.user.is_authenticated,
                'last_updated': timezone.now().isoformat(),
                'is_empty': True,
                'message': 'Your cart is empty'
            }
        
        # Process non-empty cart
        items = []
        subtotal = Decimal('0.00')
        total_items = 0
        
        for product_key, item_data in redis_cart_data.items():
            try:
                product_id = item_data.get('product_id')
                if not product_id:
                    continue
                
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    logger.error(f"Product {product_id} does not exist, removing from cart")
                    del redis_cart_data[product_key]
                    continue
                
                quantity = item_data.get('quantity', 1)
                price = Decimal(item_data.get('price', '0.00'))
                item_total = price * quantity
                
                # Get database cart item if exists
                cart_item = None
                cart_id = None
                cart_item_id = None
                
                if self.user and self.user.is_authenticated:
                    try:
                        cart_item = CartItem.objects.filter(
                            cart__user=self.user,
                            product=product,
                            selected_size=item_data.get('selected_size'),
                            selected_color=item_data.get('selected_color'),
                            selected_height=item_data.get('selected_height')
                        ).first()
                        
                        if cart_item:
                            cart_id = cart_item.cart.cart_id
                            cart_item_id = cart_item.id
                    except Exception as e:
                        logger.error(f"Error fetching database cart item: {str(e)}")
                
                items.append({
                    'variant_key': product_key,
                    'cart_id': cart_id,
                    'cart_item_id': cart_item_id,
                    'product_id': int(product_id),
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'price': float(price),
                        'image': product.image.url if product.image else None,
                        'handle': product.handle,
                        'stock': product.stock,
                        'product_colors': product.product_colors,
                        'product_sizes': product.product_sizes
                    },
                    'quantity': quantity,
                    'selected_size': item_data.get('selected_size'),
                    'selected_color': item_data.get('selected_color'),
                    'selected_height': item_data.get('selected_height'),
                    'price': float(price),
                    'total_price': float(item_total),
                    'max_quantity': product.stock,
                    'added_at': item_data.get('added_at'),
                    'is_available': product.stock > 0
                })
                
                subtotal += item_total
                total_items += quantity
                
            except Exception as e:
                logger.error(f"Error processing Redis item {product_key}: {e}")
                continue
        
        # Update metadata
        metadata['items_count'] = len(items)
        metadata['total_amount'] = str(subtotal)
        metadata['status'] = 'active'
        self._cache_set(self.metadata_key, metadata)
        
        # Save updated Redis cart if we made changes
        if redis_cart_data != self._cache_get(self.redis_key):
            self._cache_set(self.redis_key, redis_cart_data)
        
        return {
            'cart_key': self.cart_key,
            'items': items,
            'summary': {
                'subtotal': float(subtotal),
                'total_items': total_items,
                'item_count': len(items),
                'estimated_tax': float(subtotal * Decimal('0.075')),
                'shipping': float(Decimal('500.00') if subtotal > 0 else Decimal('0.00')),
                'total': float(subtotal + (subtotal * Decimal('0.075')) + 
                              (Decimal('500.00') if subtotal > 0 else Decimal('0.00')))
            },
            'metadata': metadata,
            'is_authenticated': self.user and self.user.is_authenticated,
            'last_updated': timezone.now().isoformat(),
            'is_empty': False,
            'message': f'Your cart has {len(items)} items'
        }
    
    def is_cart_empty(self):
        """Check if cart is empty"""
        redis_cart_data = self._cache_get(self.redis_key) or {}
        return not bool(redis_cart_data)
    
    def clear_cart_for_user(self, user_id):
        """Clear cart for a specific user (for webhook use)"""
        try:
            # Clear by user ID
            user_cart_key = f"{self.CART_PREFIX}user_{user_id}"
            user_metadata_key = f"{user_cart_key}:metadata"
            
            # Delete from Redis
            cache.delete(user_cart_key)
            cache.delete(user_metadata_key)
            
            logger.info(f" Cleared Redis cart for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cart for user {user_id}: {str(e)}")
            return False
    
    def clear_cart(self):
        """ IMPROVED: Clear cart from Redis and Database with proper cleanup"""
        try:
            # Clear Redis cache
            cache.delete(self.redis_key)
            cache.delete(self.metadata_key)
            logger.info(f" Cleared Redis cart: {self.redis_key}")
            
            # Clear from session if exists
            if self.request:
                self.request.session.pop('cart_key', None)
                logger.info(f" Cleared cart_key from session")
            
            # Clear from database if user is authenticated
            if self.user and self.user.is_authenticated:
                try:
                    cart = Cart.objects.filter(user=self.user).first()
                    if cart:
                        # Delete cart items first
                        items_count = cart.cart_items.count()
                        cart.cart_items.all().delete()
                        logger.info(f" Deleted {items_count} cart items from database")
                        
                        # Delete cart
                        cart.delete()
                        logger.info(f" Deleted cart from database for user: {self.user.id}")
                except Exception as e:
                    logger.error(f" Error deleting cart from database: {str(e)}")
            
            logger.info(f" Cart cleared successfully for key: {self.cart_key}")
            return True, "Cart cleared successfully"
            
        except Exception as e:
            logger.error(f" Error clearing cart: {e}")
            return False, str(e)
    
    #  NEW: Handle user logout
    def handle_user_logout(self):
        """
        Handle user logout - clear cart from both Redis and Database
        """
        try:
            if self.user and self.user.is_authenticated:
                user_id = self.user.id
                
                # Clear Redis cart
                cache.delete(self.redis_key)
                cache.delete(self.metadata_key)
                logger.info(f" Cleared Redis cart on logout for user: {user_id}")
                
                # Clear database cart
                cart = Cart.objects.filter(user=self.user).first()
                if cart:
                    cart.cart_items.all().delete()
                    cart.delete()
                    logger.info(f" Cleared database cart on logout for user: {user_id}")
                
                # Clear session cart key
                if self.request:
                    self.request.session.pop('cart_key', None)
                
                return True, "Logout handled successfully - cart cleared"
            
            # For anonymous users, clear everything
            return self.clear_cart()
            
        except Exception as e:
            logger.error(f" Error handling user logout: {str(e)}")
            return False, str(e)
    
    #  NEW: Periodic cleanup task
    def cleanup_orphaned_carts(self):
        """
        Clean up carts where Redis is empty but Database has items
        This should be called periodically (e.g., via Celery task or cron job)
        """
        try:
            cleaned_count = 0
            
            # Get all database carts
            all_carts = Cart.objects.all()
            
            for cart in all_carts:
                try:
                    # Check if Redis has data for this cart
                    redis_key = f"{self.CART_PREFIX}user_{cart.user.id}"
                    redis_cart_data = cache.get(redis_key)
                    
                    # If Redis is empty but database has items
                    if not redis_cart_data and cart.cart_items.exists():
                        logger.warning(f"Found orphaned cart for user {cart.user.id}. Cleaning up...")
                        
                        # Delete cart items and cart
                        cart.cart_items.all().delete()
                        cart.delete()
                        
                        cleaned_count += 1
                        logger.info(f" Cleaned orphaned cart for user {cart.user.id}")
                        
                except Exception as e:
                    logger.error(f" Error cleaning cart for user {cart.user.id}: {str(e)}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} orphaned carts")
            return cleaned_count
            
        except Exception as e:
            logger.error(f" Error in cleanup_orphaned_carts: {str(e)}")
            return 0
    
    def mark_cart_as_abandoned(self):
        """Mark cart as abandoned (for analytics)"""
        metadata = self._cache_get(self.metadata_key) or {}
        metadata['abandoned'] = True
        metadata['abandoned_at'] = timezone.now().isoformat()
        metadata['status'] = 'abandoned'
        self._cache_set(self.metadata_key, metadata, timeout=self.ABANDONED_CART_TTL)
        
        # Also reduce TTL for the cart itself
        redis_cart_data = self._cache_get(self.redis_key)
        if redis_cart_data:
            self._cache_set(self.redis_key, redis_cart_data, timeout=self.ABANDONED_CART_TTL)
        
        logger.info(f"Cart marked as abandoned: {self.cart_key}")
        return True
    
    def sync_with_database_cart(self):
        """IMPROVED: Sync Redis cart with database cart"""
        if not self.user or not self.user.is_authenticated:
            return None
        
        try:
            # Get Redis cart data
            redis_cart_data = self._cache_get(self.redis_key) or {}
            
            # If Redis cart is empty, clean up database cart
            if not redis_cart_data:
                cart = Cart.objects.filter(user=self.user).first()
                if cart and cart.cart_items.exists():
                    cart.cart_items.all().delete()
                    cart.delete()
                    logger.info(f" Cleaned up database cart for user {self.user.id} - Redis was empty")
                return None
            
            # Get or create database cart
            cart, created = Cart.objects.get_or_create(user=self.user)
            
            # Sync items to database from Redis
            synced_item_ids = set()
            
            for variant_key, item_data in redis_cart_data.items():
                try:
                    product_id = item_data.get('product_id')
                    if not product_id:
                        continue
                        
                    product = Product.objects.get(id=product_id)
                    
                    # Get item details
                    selected_size = item_data.get('selected_size')
                    selected_color = item_data.get('selected_color')
                    selected_height = item_data.get('selected_height')
                    quantity = item_data.get('quantity', 1)
                    
                    # Try to find existing cart item
                    cart_item = CartItem.objects.filter(
                        cart=cart,
                        product=product,
                        selected_size=selected_size,
                        selected_color=selected_color,
                        selected_height=selected_height
                    ).first()
                    
                    if cart_item:
                        cart_item.quantity = quantity
                        cart_item.save()
                        synced_item_ids.add(cart_item.id)
                    else:
                        cart_item = CartItem.objects.create(
                            cart=cart,
                            product=product,
                            quantity=quantity,
                            selected_size=selected_size,
                            selected_color=selected_color,
                            selected_height=selected_height
                        )
                        synced_item_ids.add(cart_item.id)
                        
                except (Product.DoesNotExist, ValueError) as e:
                    logger.error(f"Error syncing cart item: {str(e)}")
                    continue
            
            # Delete any cart items that are no longer in Redis
            if redis_cart_data:
                deleted_count = cart.cart_items.exclude(id__in=synced_item_ids).delete()[0]
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} stale cart items from database")
            
            logger.info(f"Synced cart for user {self.user.id}: {len(synced_item_ids)} items")
            return cart
            
        except Exception as e:
            logger.error(f" Error syncing cart with database: {e}")
            return None