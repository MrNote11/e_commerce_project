"""
Signals for automatic model creation and updates.
This file must be imported in apps.py ready() method.
"""
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.db.models import Avg
import logging
from .models import Reviews, Product, Category, CartItem, ProductRating
from django.utils.cache import get_cache_key
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from stock.models import Cart
from e_commerce.modules.redis_cart import RedisCartService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Reviews)
def update_product_rating_review(sender, instance, created, **kwargs):
    """Update product rating when review is created or updated"""
    product = instance.product
    reviews = product.product_reviews.all()
    total_reviews = reviews.count()
    
    review_average = reviews.aggregate(Avg('ratings'))['ratings__avg'] or 0.0
    
    product_rating, created = ProductRating.objects.get_or_create(product=product)
    product_rating.average_rating = review_average 
    product_rating.total_reviews = total_reviews 
    product_rating.save()


@receiver(post_delete, sender=Reviews)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """Update product rating when review is deleted"""
    product = instance.product 
    reviews = product.product_reviews.all()
    total_reviews = reviews.count()
    
    review_average = reviews.aggregate(Avg("ratings"))["ratings__avg"] or 0.0
    
    product_rating, created = ProductRating.objects.get_or_create(product=product)
    product_rating.average_rating = review_average 
    product_rating.total_reviews = total_reviews 
    product_rating.save()


@receiver(user_logged_out)
def cleanup_cart_on_logout(sender, request, user, **kwargs):
    """
     Automatically cleanup cart when user logs out
    """
    try:
        if user:
            cart_service = RedisCartService(user=user)
            success, message = cart_service.handle_user_logout()
            
            if success:
                logger.info(f" Cart cleared on logout for user: {user.id}")
            else:
                logger.warning(f"⚠️ Cart cleanup failed on logout for user: {user.id}")
                
    except Exception as e:
        logger.error(f" Error in logout signal: {str(e)}")


@receiver(pre_delete, sender=Cart)
def cleanup_redis_on_cart_delete(sender, instance, **kwargs):
    """
     Clear Redis cart when database cart is deleted
    """
    try:
        if instance.user:
            cart_service = RedisCartService(user=instance.user)
            cart_service.clear_cart_for_user(instance.user.id)
            logger.info(f" Cleared Redis on cart deletion for user: {instance.user.id}")
            
    except Exception as e:
        logger.error(f" Error clearing Redis on cart delete: {str(e)}")


