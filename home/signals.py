# signals.py (create this file)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, UserOTP

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create empty UserProfile when User is created"""
    if created and not hasattr(instance, 'userprofile'):
        UserProfile.objects.create(user=instance, email=instance.email)
        
        
@receiver(post_save, sender=UserProfile)
def create_user_otp(sender, instance, created, **kwargs):
    if created:
        UserOTP.objects.create(userprofile=instance, email=instance.email, phoneNumber=instance.phoneNumber)


# Don't forget to import signals in your apps.py