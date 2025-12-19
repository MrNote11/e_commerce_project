"""
Signals for automatic model creation and updates.
This file must be imported in apps.py ready() method.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from home.models import User, UserProfile, UserOTP
from .models import UserProfile, UserOTP
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            # Check if profile already exists (edge case)
            
                UserProfile.objects.create(
                    user=instance,
                    email=instance.email
                )
                logger.info(f"UserProfile created for user {instance.id} ({instance.email})")
   
        except Exception as e:
            logger.error(f"Failed to create UserProfile for user {instance.id}: {e}")

