from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
# Create your models here.

GENDER_TYPE_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
)

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

    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)

    image = models.ImageField(upload_to="profile-picture", blank=True, null=True)
    active = models.BooleanField(default=False)
    dateCreated = models.DateTimeField(auto_now_add=True)

    # Track login
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

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
