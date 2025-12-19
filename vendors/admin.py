from stock.models import Product
from django.contrib import admin
from .models import (
    VendorAnalytics, VendorSalesRecord, 
    ProductPerformance, VendorNotification, VendorProfile
)


@admin.register(VendorAnalytics)
class VendorAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'date', 'total_sales', 'total_orders', 'total_customers']
    list_filter = ['date', 'vendor']
    search_fields = ['vendor__store_name']
    date_hierarchy = 'date'
    readonly_fields = ['date', 'updated_at']


@admin.register(VendorSalesRecord)
class VendorSalesRecordAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'date', 'orders_count', 'revenue', 'new_customers', 'returning_customers']
    list_filter = ['date', 'vendor']
    search_fields = ['vendor__store_name']
    date_hierarchy = 'date'


@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = ['product', 'total_orders', 'total_revenue', 'average_rating', 'updated_at']
    list_filter = ['updated_at', 'product__vendor']
    search_fields = ['product__name', 'product__vendor__store_name']
    readonly_fields = ['updated_at']


@admin.register(VendorNotification)
class VendorNotificationAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['vendor__store_name', 'title', 'message']
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected notifications as unread"
    
admin.site.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['store_name', 'user__username', 'user__email']
    # list_editable = ['price', 'available']
    