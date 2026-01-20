from django.utils.deprecation import MiddlewareMixin
from e_commerce.modules.redis_cart import RedisCartService
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class ProductCacheMiddleware(MiddlewareMixin):
    """
    Middleware for caching product views
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if this is a product detail view
        if 'pk' in view_kwargs and hasattr(view_func, '__name__'):
            if view_func.__name__ == 'ProductDetailViews':
                # Check cache first
                cache_key = f'product_detail_{view_kwargs["pk"]}'
                cached_data = cache.get(cache_key)
                
                if cached_data:
                    # You could log cache hits here
                    pass
        return None


class CartMiddleware(MiddlewareMixin):
    """
    Middleware for cart operations
    """
    
    def process_request(self, request):
        # Initialize cart service for authenticated users
        if request.user.is_authenticated:
            try:
                cart_service = RedisCartService(request=request)
                # Update last activity
                cart_service._update_metadata(last_activity=cart_service._get_current_time())
            except Exception as e:
                logger.error(f"Error in cart middleware: {e}")
    
    def process_response(self, request, response):
        # Handle cart merging on login
        if (request.user.is_authenticated and 
            request.path in ['/api/auth/login/', '/api/auth/token/', '/home/login/'] and 
            response.status_code == 200):
            
            try:
                # Get anonymous cart from session
                anonymous_cart_key = request.session.get('cart_key')
                
                if anonymous_cart_key and not anonymous_cart_key.startswith('user_'):
                    # Create user cart service
                    user_cart_service = RedisCartService(request=request)
                    
                    # Sync database cart
                    user_cart_service.sync_with_database_cart()
                    
            except Exception as e:
                logger.error(f"Error merging carts on login: {e}")
        
        return response
    
    
class CartSyncMiddleware(MiddlewareMixin):
    """
     Middleware to ensure Redis and Database carts are in sync
    This runs on every request for authenticated users
    """
    
    def process_request(self, request):
        """Sync cart on every request if user is authenticated"""
        try:
            # Only sync for authenticated users
            if request.user.is_authenticated:
                # Only sync on cart-related endpoints or specific pages
                cart_endpoints = ['/api/cart/', '/checkout', '/cart']
                
                if any(endpoint in request.path for endpoint in cart_endpoints):
                    cart_service = RedisCartService(request=request)
                    
                    # This will automatically restore from DB if Redis is empty
                    cart_service._ensure_redis_db_sync()
                    
        except Exception as e:
            # Don't break the request if sync fails
            logger.error(f"Cart sync middleware error: {str(e)}")
            pass
        
        return None