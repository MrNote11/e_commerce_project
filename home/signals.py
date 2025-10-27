"""
Signals for automatic model creation and updates.
This file must be imported in apps.py ready() method.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, UserOTP
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when a User is created.
    This ensures every user has a profile.
    """
    if created:
        try:
            # Check if profile already exists (edge case)
            if not hasattr(instance, 'userprofile'):
                UserProfile.objects.create(
                    user=instance,
                    email=instance.email
                )
                logger.info(f"✅ UserProfile created for user {instance.id} ({instance.email})")
            else:
                logger.info(f"ℹ️ UserProfile already exists for user {instance.id}")
        except Exception as e:
            logger.error(f"❌ Failed to create UserProfile for user {instance.id}: {e}")


@receiver(post_save, sender=UserProfile)
def create_user_otp(sender, instance, created, **kwargs):
    """
    Automatically create UserOTP when a UserProfile is created.
    This ensures every profile has an OTP record.
    """
    if created:
        try:
            # Check if OTP record already exists
            if not UserOTP.objects.filter(userprofile=instance).exists():
                UserOTP.objects.create(
                    userprofile=instance,
                    email=instance.email,
                    phoneNumber=instance.phoneNumber
                )
                logger.info(f"✅ UserOTP created for profile {instance.id}")
            else:
                logger.info(f"ℹ️ UserOTP already exists for profile {instance.id}")
        except Exception as e:
            logger.error(f"❌ Failed to create UserOTP for profile {instance.id}: {e}")