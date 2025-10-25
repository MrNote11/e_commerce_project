from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

GENDER_TYPE_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
)

# class User(AbstractUser):
#     is_active = models.BooleanField(default=False)  # Important: default=False
   
#     class Meta:
#         db_table = 'home_user'  # Explicitly set the table name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    email = models.EmailField(max_length=255, blank=True, null=True)
    otherName = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(
        max_length=20, choices=GENDER_TYPE_CHOICES, blank=True, null=True
    )
    dob = models.DateField(null=True, blank=True)
    phoneNumber = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=300, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)

    image = models.ImageField(upload_to="profile-picture", blank=True, null=True)
    active = models.BooleanField(default=True)
    dateCreated = models.DateTimeField(auto_now_add=True)

    # Track login
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def generate_verification_token(self):
        """Generate a unique verification token"""
        import secrets
        token = secrets.token_urlsafe(32)
        self.verification_token = token
        self.verification_sent_at = timezone.now()
        self.save()
        return token
    
    def is_verification_token_expired(self):
        """Check if verification token is expired (24 hours)"""
        if not self.verification_sent_at:
            return True
        expiration_time = self.verification_sent_at + timedelta(hours=24)
        return timezone.now() > expiration_time
    
    def get_lockout_remaining(self):
        if self.is_locked():
            remaining = self.locked_until - timezone.now()
            return max(0, int(remaining.total_seconds()))
        return 0
    
    def __str__(self):
        return f"{self.user.username}"

class UserOTP(models.Model):
    phoneNumber = models.CharField(max_length=24, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    otp = models.TextField(help_text="Encrypted OTP Value", blank=True, null=True)
    expiry = models.DateTimeField(blank=True, null=True)
    dateCreated = models.DateTimeField(auto_now_add=True)
    dateUpdated = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        if self.phoneNumber:
            return f"{self.phoneNumber}"
        return f"{self.email}"