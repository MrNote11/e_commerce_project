# signals.py (create this file)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create empty UserProfile when User is created"""
    if created and not hasattr(instance, 'userprofile'):
        UserProfile.objects.create(user=instance, email=instance.email)
        
# Don't forget to import signals in your apps.py 