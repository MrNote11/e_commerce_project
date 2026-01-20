from django.db import models
# Create your models here.
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Avg, F, Q, Count
from datetime import timedelta



class VendorProfile(models.Model):
    user = models.OneToOneField('home.User', on_delete=models.CASCADE, related_name='vendor_profile')
    store_name = models.CharField(max_length=100, unique=True)  # Increased length
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verification_sent_at = models.DateTimeField(auto_now_add=True)
    locked_until = models.DateTimeField(null=True, blank=True)  # Added missing field
    
    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def generate_vendor_verification_token(self):
        import secrets
        token = secrets.token_urlsafe(32)
        self.verification_token = token
        self.verification_sent_at = timezone.now()
        self.save()
        return token
    
    def is_verification_token_expired(self):
        if not self.verification_sent_at:
            return True
        expiration_time = self.verification_sent_at + timedelta(hours=24)
        return timezone.now() > expiration_time
    
    def get_lockout_remaining(self):
        if self.is_locked():
            remaining = self.locked_until - timezone.now()
            return max(0, int(remaining.total_seconds()))
        return 0
    
    def is_complete(self):
        required_fields = [
            self.address,
            self.description,
            self.store_name,  # Fixed: was business_name
            self.contact_phone,  # Fixed: was phone
        ]
        return all(bool(field) for field in required_fields)
      
    def __str__(self):
        return f"{self.store_name} - {self.user.email}"



class VendorAnalytics(models.Model):
    """Store vendor analytics data"""
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='analytics')
    
    # Sales metrics
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    weekly_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Order metrics
    total_orders = models.PositiveIntegerField(default=0)
    pending_orders = models.PositiveIntegerField(default=0)
    successful_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    
    # Product metrics
    total_products = models.PositiveIntegerField(default=0)
    out_of_stock_products = models.PositiveIntegerField(default=0)
    low_stock_products = models.PositiveIntegerField(default=0)
    
    # Customer metrics
    total_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    returning_customer_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Financial metrics
    gross_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    processing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Time tracking
    date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['vendor', 'date']
        indexes = [
            models.Index(fields=['vendor', '-date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.vendor.store_name} - {self.date}"
    
    @classmethod
    def calculate_for_vendor(cls, vendor, date=None):
        """Calculate analytics for a vendor"""
        from django.apps import apps
        
        # Get models using string references
        Order = apps.get_model('stock', 'Order')
        Product = apps.get_model('stock', 'Product')
        
        if date is None:
            date = timezone.now().date()
        
        # Get or create analytics record
        analytics, created = cls.objects.get_or_create(
            vendor=vendor,
            date=date
        )
        
        # Calculate weekly sales
        week_start = date - timedelta(days=date.weekday())
        weekly_orders = Order.objects.filter(
            items__product__vendor=vendor,
            status='Paid',
            created_at__date__gte=week_start,
            created_at__date__lte=date
        ).distinct()
        
        analytics.weekly_sales = weekly_orders.aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    # ... rest of the method remains the same
    # All Order and Product references will now work
        
        # Calculate monthly sales
        month_start = date.replace(day=1)
        monthly_orders = Order.objects.filter(
            items__product__vendor=vendor,
            status='Paid',
            created_at__date__gte=month_start,
            created_at__date__lte=date
        ).distinct()
        
        analytics.monthly_sales = monthly_orders.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate total sales (all time)
        all_orders = Order.objects.filter(
            items__product__vendor=vendor,
            status='Paid'
        ).distinct()
        
        analytics.total_sales = all_orders.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Order metrics
        vendor_orders = Order.objects.filter(
            items__product__vendor=vendor
        ).distinct()
        
        analytics.total_orders = vendor_orders.count()
        analytics.pending_orders = vendor_orders.filter(status='Pending').count()
        analytics.successful_orders = vendor_orders.filter(status='Paid').count()
        
        # Product metrics
        vendor_products = Product.objects.filter(vendor=vendor)
        analytics.total_products = vendor_products.count()
        analytics.out_of_stock_products = vendor_products.filter(stock=0).count()
        analytics.low_stock_products = vendor_products.filter(stock__gt=0, stock__lte=5).count()
        
        # Customer metrics
        customer_ids = vendor_orders.values_list('user_id', flat=True).distinct()
        analytics.total_customers = len(set(customer_ids))
        
       
        returning = vendor_orders.values('user').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count()
        
        analytics.returning_customers = returning
        if analytics.total_customers > 0:
            analytics.returning_customer_rate = (
                returning / analytics.total_customers * 100
            )
        
        # Financial metrics
        analytics.gross_sale = analytics.total_sales
        
        analytics.save()
        return analytics


class VendorSalesRecord(models.Model):
    """Daily sales records for trend analysis"""
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='sales_records')
    date = models.DateField()
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['vendor', 'date']
        ordering = ['date']
        indexes = [
            models.Index(fields=['vendor', 'date']),
        ]
    
    def __str__(self):
        return f"{self.vendor.store_name} - {self.date}"


class ProductPerformance(models.Model):
    """Track individual product performance"""
    product = models.OneToOneField('stock.Product', on_delete=models.CASCADE, related_name='performance')
    
    # Sales metrics
    total_orders = models.PositiveIntegerField(default=0)
    total_quantity_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Percentage metrics
    order_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    revenue_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Engagement metrics
    wishlist_count = models.PositiveIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_revenue']
        indexes = [
            models.Index(fields=['-total_revenue']),
            models.Index(fields=['-total_orders']),
        ]
    
    def __str__(self):
        return f"{self.product.name} Performance"
    
    @classmethod
    def update_for_product(cls, product):
        """Update performance metrics for a product"""
        from django.apps import apps
        
        # Get models using string references
        Order = apps.get_model('stock', 'Order')
        OrderItem = apps.get_model('stock', 'OrderItem')
        Wishlist = apps.get_model('stock', 'Wishlist')
        Reviews = apps.get_model('stock', 'Reviews')
        
        performance, created = cls.objects.get_or_create(product=product)
        
        # Get order items for this product
        order_items = OrderItem.objects.filter(
            product=product,
            order__status='Paid'
        )
    
    # ... rest of the method remains the same
        
        performance.total_orders = order_items.values('order').distinct().count()
        performance.total_quantity_sold = order_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        performance.total_revenue = order_items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or 0
        
        # Calculate percentages relative to vendor
        vendor_total_orders = Order.objects.filter(
            items__product__vendor=product.vendor,
            status='Paid'
        ).distinct().count()
        
        if vendor_total_orders > 0:
            performance.order_percentage = (
                performance.total_orders / vendor_total_orders * 100
            )
        
        vendor_total_revenue = Order.objects.filter(
            items__product__vendor=product.vendor,
            status='Paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if vendor_total_revenue > 0:
            performance.revenue_percentage = (
                float(performance.total_revenue) / float(vendor_total_revenue) * 100
            )
        
        # Engagement metrics
        from stock.models import Wishlist, Reviews
        performance.wishlist_count = Wishlist.objects.filter(product=product).count()
        performance.review_count = Reviews.objects.filter(product=product).count()
        
        avg_rating = Reviews.objects.filter(product=product).aggregate(
            avg=Avg('ratings')
        )['avg']
        performance.average_rating = avg_rating or 0
        
        performance.save()
        return performance


class VendorNotification(models.Model):
    """Notifications for vendor dashboard"""
    TYPE_CHOICES = [
        ('order', 'New Order'),
        ('low_stock', 'Low Stock Alert'),
        ('out_of_stock', 'Out of Stock'),
        ('review', 'New Review'),
        ('payment', 'Payment Received'),
        ('system', 'System Notification'),
    ]
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"{self.vendor.store_name} - {self.title}"
