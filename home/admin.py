from django.contrib import admin
from home.models import User, UserProfile, UserOTP
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.
from home.models import User, UserProfile, UserOTP
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
admin.site.register(UserProfile)
admin.site.register(UserOTP)
