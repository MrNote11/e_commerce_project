# permissions.py
from rest_framework import permissions

class IsVendor(permissions.BasePermission):
    """Check if user is a vendor"""
    def has_permission(self, request, view):
        return hasattr(request.user, 'vendor_profile')

class IsVendorOwner(permissions.BasePermission):
    """Check if user owns the vendor profile"""
    def has_object_permission(self, request, view, obj):
        return obj.vendor.user == request.user

class IsApprovedVendor(permissions.BasePermission):
    """Check if vendor is approved"""
    def has_permission(self, request, view):
        return hasattr(request.user, 'vendor_profile') and request.user.vendor_profile.is_approved
    
class CanManageProduct(permissions.BasePermission):
    """Vendor must own the product and have a completed profile."""

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Check ownership
        if obj.vendor.user != user:
            return False

        # Get vendor profile safely
        profile = getattr(user, "vendor_profile", None)

        if not profile:
            return False

        # Require completed profile
        return profile.is_complete()

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
