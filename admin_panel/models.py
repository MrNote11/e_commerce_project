from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
import secrets
from django.utils import timezone

User = get_user_model()


class AdminRole(models.Model):
    """Model for admin roles with feature permissions"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    features = models.JSONField(default=dict)  # Store feature permissions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class AdminUser(models.Model):
    """Model for admin users with additional permissions"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(
        AdminRole,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_users'
    )
    is_super_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Track login
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Admin User')
        verbose_name_plural = _('Admin Users')
        indexes = [
            models.Index(fields=['is_super_admin']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} (Admin)"

    def has_feature_permission(self, feature):
        """Check if admin has permission for a specific feature"""
        if self.is_super_admin:
            return True
        return self.role and feature in self.role.features

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def get_lockout_remaining(self):
        if self.is_locked():
            remaining = self.locked_until - timezone.now()
            return max(0, int(remaining.total_seconds()))
        return 0

    @staticmethod
    def generate_password():
        """Generate a secure random password"""
        return secrets.token_urlsafe(12)  # 16 characters


class CustomerReview(models.Model):
    """Model for customer reviews"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review_text = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Customer Review')
        verbose_name_plural = _('Customer Reviews')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Review by {self.user.email} - {self.rating} stars"


class BlacklistedAccount(models.Model):
    """Model for blacklisted user accounts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    blacklisted_by = models.ForeignKey(
        AdminUser,
        on_delete=models.SET_NULL,
        null=True
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Blacklisted Account')
        verbose_name_plural = _('Blacklisted Accounts')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
            models.Index(fields=['blacklisted_at']),
        ]

    def __str__(self):
        return f"Blacklisted: {self.user.email}"


class UserActivity(models.Model):
    """Model for tracking user activities"""
    ACTIVITY_TYPES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('VENDORS', 'Create/Update/Delete Vendor Profile'),
        # ('WITHDRAWAL', 'Withdrawal'),
        # ('INVESTMENT', 'Investment'),
        # ('KYC_UPDATE', 'KYC Update'),
        # ('BANK_OPERATION', 'Create/Update/Delete Bank'),
        # ('CARD_OPERATION', 'Create/Update/Delete Payment Card'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PROFILE_UPDATE', 'Profile Update'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.activity_type} - {self.created_at}"


class BVNVerificationAttempt(models.Model):
    """Model for tracking BVN verification attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bvn = models.CharField(max_length=11)
    status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
            ('PENDING', 'Pending')
        ],
        default='PENDING'
    )
    attempt_count = models.IntegerField(default=1)
    last_attempt_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('BVN Verification Attempt')
        verbose_name_plural = _('BVN Verification Attempts')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"BVN Verification Attempt for {self.user.email}"
