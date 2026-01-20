# serializers.py
from rest_framework import serializers
from stock.admin import User
from stock.models import Product, Category
from e_commerce.modules.email_utils import send_vendor_verification_email
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from django.core.validators import MinValueValidator
import re
from stock.models import Order, OrderItem, Product, Cart, Reviews
from vendors.models import VendorProfile
from .models import VendorAnalytics, VendorSalesRecord, ProductPerformance, VendorNotification

class VendorProfileSerializer(serializers.ModelSerializer):
    
    def validate_contact_email(self, value):
        if VendorProfile.objects.filter(contact_email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_user(self, attrs):
        data = User.objects.get(id=attrs)
        if VendorProfile.objects.filter(user=data).exists():
            raise serializers.ValidationError("Username already exists.")
        
    def validate_store_name(self, value):
        if VendorProfile.objects.filter(store_name=value).exists():
            raise serializers.ValidationError("Store name already exists.")
        return value
    
    def validate_contact_phone(self, data):
        if not data.isdigit() or len(data) != 11:
            raise serializers.ValidationError("Invalid phone number.")
        
        if VendorProfile.objects.filter(contact_phone=data).exists():
            raise serializers.ValidationError("Phone number already exists.")
        
        return data
    
    def validate_store_handle(self, value):
        if VendorProfile.objects.filter(store_handle=value).exists():
            raise serializers.ValidationError("Store handle already exists.")
        return value
    
    class Meta:
        model = VendorProfile
        fields = ['id', 'user', 'store_name', 'description', 
                 'is_approved', 'contact_email', 'contact_phone', 'address', 
                 'created_at', 'updated_at']
        read_only_fields = ['is_approved', 'created_at', 'updated_at']
        
        
class VendorCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(required=False, write_only=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        
        # If user_id is provided in payload, check if admin user
        if 'user_id' in attrs and attrs['user_id']:
            if not request.user.is_staff and not request.user.is_superuser:
                raise serializers.ValidationError({
                    "user_id": "Only admin users can specify user ID for vendor creation"
                })
            
            # Check if the specified user exists
            try:
                user = User.objects.get(id=attrs['user_id'])
                attrs['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    "user_id": "User with this ID does not exist"
                })
        
        # Remove user_id from attrs as it's not a model field
        attrs.pop('user_id', None)
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = validated_data.get('user')
        
        # If no user specified in payload (non-admin case)
        if not user:
            if request and request.user.is_authenticated:
                user = request.user
                # Check if user already has a vendor profile
                if hasattr(user, 'vendor_profile'):
                    raise serializers.ValidationError("You are already registered as a vendor.")
            else:
                raise serializers.ValidationError("User authentication required")
        
        # Check if the assigned user already has a vendor profile
        if hasattr(user, 'vendor_profile'):
            raise serializers.ValidationError(f"User {user.username} is already registered as a vendor.")
        
        # Assign user to validated_data
        validated_data['user'] = user
        
        # Create vendor profile
        vendor_profile = VendorProfile.objects.create(**validated_data)
        vendor_profile_token = vendor_profile.generate_vendor_verification_token()
        base_url = request.build_absolute_uri('/').rstrip('/')
        vendor_profile_url = f"{base_url}/verify-email/?token={vendor_profile_token}"
        email=vendor_profile.user.email
        print(f"email: {email}")
        
        
        send_vendor_verification_email(email, vendor_profile_url)
        
        return vendor_profile
    
    class Meta:
        model = VendorProfile
        fields = ['user_id', 'store_name', 'description', 
                 'contact_email', 'contact_phone', 'address']
        extra_kwargs = {
            'user': {'read_only': True}
        }

class ProductSerializer(serializers.ModelSerializer):
    height = serializers.CharField(read_only=True)
  

    class Meta:
        model = Product
        fields = [
            'id', 'vendor', 'category', 'name', 'handle', 'description',
            'price', 'default_price', 'stock', 'image',
            'product_sizes', 'product_colors', 'in_stock',
            'height', 'timestamp', 'item_subtotal'
        ]
        read_only_fields = ['id', 'vendor', 'handle', 'default_price', 'timestamp', 'created_at']


    def validate_height_format(self, height_str):
        """Validate height format (e.g., 5.10, 6.2, 5.8)"""
        if not height_str:
            raise serializers.ValidationError("Height is required")
            
        height_pattern = r'^\d+\.\d{1,2}$'
        if not re.match(height_pattern, str(height_str)):
            raise serializers.ValidationError(
                "Height must be in format: feet.inches (e.g., 5.10, 6.2)"
            )
        
        try:
            height_float = float(height_str)
            if height_float < 3.0 or height_float > 8.0:
                raise serializers.ValidationError("Height must be between 3.0 and 8.0 feet")
        except ValueError:
            raise serializers.ValidationError("Height must be a valid number")
        
        return height_str
    

    def validate_product_sizes(self, value):
        """Validate product_sizes has multiple sizes, each with REQUIRED height"""
        if not value:
            raise serializers.ValidationError("product_sizes is required")
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("product_sizes must be a dictionary")
        
        # Allow 1-3 sizes (flexible)
        if len(value) == 0 or len(value) > 3:
            raise serializers.ValidationError("product_sizes must contain 1 to 3 sizes")
        
        valid_sizes = [size[0] for size in Product.SIZE_CHOICES]
        
        # Validate EACH size has its own height
        for size_key, size_data in value.items():
            # Validate size key
            if size_key not in valid_sizes:
                raise serializers.ValidationError(
                    f"Invalid size '{size_key}'. Must be one of: {', '.join(valid_sizes)}"
                )
            
            # Validate size data structure
            if not isinstance(size_data, dict):
                raise serializers.ValidationError(f"Size data for '{size_key}' must be a dictionary")
            
            # Validate height exists for this size
            if 'height' not in size_data:
                raise serializers.ValidationError(f"Height is required for size '{size_key}'")
            
            # Validate height format for this size
            height_value = size_data['height']
            if not height_value:
                raise serializers.ValidationError(f"Height cannot be empty for size '{size_key}'")
            
            self.validate_height_format(height_value)
        
        return value


    def validate_product_colors(self, value):
        """Validate product_colors dictionary with color quantities"""
        if value:
            if not isinstance(value, dict):
                raise serializers.ValidationError("product_colors must be a dictionary")
            
            valid_colors = [color[0] for color in Product.COLOR_CHOICES]
            
            for color_name, quantity in value.items():
                # Validate color name
                if color_name not in valid_colors:
                    raise serializers.ValidationError(
                        f"Invalid color '{color_name}'. Must be one of: {', '.join(valid_colors)}"
                    )
                
                # FIX: Handle both integer and string quantities
                try:
                    # Convert string to integer if needed
                    if isinstance(quantity, str):
                        quantity = int(quantity)
                    elif not isinstance(quantity, int):
                        raise ValueError("Quantity must be convertible to integer")
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"Quantity for '{color_name}' must be a valid integer")
                
                # Validate quantity constraints: minimum 0, maximum 10
                if quantity < 0:
                    raise serializers.ValidationError(f"Quantity for '{color_name}' cannot be negative")
                
                if quantity > 10:
                    raise serializers.ValidationError(f"Quantity for '{color_name}' cannot exceed 10")
                
                # Update the value with converted integer
                value[color_name] = quantity
            
            # Check for duplicate colors
            if len(value) != len(set(value.keys())):
                raise serializers.ValidationError("Duplicate colors are not allowed")
        
        return value
    

    def validate(self, attrs):
        """Cross-field validation"""
        product_sizes = attrs.get('product_sizes')
        
        if not product_sizes:
            raise serializers.ValidationError({
                'product_sizes': 'product_sizes is required for all products'
            })
        
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        vendor_profile = request.user.vendor_profile
        validated_data['vendor'] = vendor_profile
        
        # Stock is now automatically calculated in the model's save method
        # based on the sum of color quantities
        
        # Create the product
        product = super().create(validated_data)
        
        return product
    
      
class CategorySerializer(serializers.ModelSerializer):
    category_product = ProductSerializer(many=True, read_only=True)
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'slug', 'category_product']
        read_only_fields = ['id']
        
        
class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image']
        read_only_fields = ['id']


class VendorAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for vendor analytics data"""
    sales_growth = serializers.SerializerMethodField()
    order_growth = serializers.SerializerMethodField()
    customer_growth = serializers.SerializerMethodField()
    product_share_target = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorAnalytics
        fields = [
            'id', 'total_sales', 'weekly_sales', 'monthly_sales',
            'total_orders', 'pending_orders', 'successful_orders', 'cancelled_orders',
            'total_products', 'out_of_stock_products', 'low_stock_products',
            'total_customers', 'returning_customers', 'returning_customer_rate',
            'gross_sale', 'refunds', 'processing_amount',
            'sales_growth', 'order_growth', 'customer_growth', 'product_share_target',
            'date', 'updated_at'
        ]
    
    def get_sales_growth(self, obj):
        """Calculate sales growth percentage"""
        try:
            previous = VendorAnalytics.objects.filter(
                vendor=obj.vendor,
                date__lt=obj.date
            ).order_by('-date').first()
            
            if previous and previous.weekly_sales > 0:
                growth = ((obj.weekly_sales - previous.weekly_sales) / previous.weekly_sales) * 100
                return round(float(growth), 2)
        except:
            pass
        return 3.5  # Default for demo
    
    def get_order_growth(self, obj):
        """Calculate order growth percentage"""
        try:
            previous = VendorAnalytics.objects.filter(
                vendor=obj.vendor,
                date__lt=obj.date
            ).order_by('-date').first()
            
            if previous and previous.total_orders > 0:
                growth = ((obj.total_orders - previous.total_orders) / previous.total_orders) * 100
                return round(float(growth), 2)
        except:
            pass
        return 13.6  # Default for demo
    
    def get_customer_growth(self, obj):
        """Calculate customer growth percentage"""
        try:
            previous = VendorAnalytics.objects.filter(
                vendor=obj.vendor,
                date__lt=obj.date
            ).order_by('-date').first()
            
            if previous and previous.returning_customer_rate > 0:
                growth = ((obj.returning_customer_rate - previous.returning_customer_rate) / previous.returning_customer_rate) * 100
                return round(float(growth), 2)
        except:
            pass
        return 3.5  # Default for demo
    
    def get_product_share_target(self, obj):
        """Calculate product share vs target"""
        # This would be based on your business logic
        # For now, returning a demo value
        return {
            'current': 34.6,
            'target': 55,
            'percentage': 62.9
        }


class VendorSalesRecordSerializer(serializers.ModelSerializer):
    """Serializer for daily sales records"""
    class Meta:
        model = VendorSalesRecord
        fields = ['date', 'new_customers', 'returning_customers', 'orders_count', 'revenue']


class ProductPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for product performance metrics"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_handle = serializers.CharField(source='product.handle', read_only=True)
    product_image = serializers.SerializerMethodField()
    category = serializers.CharField(source='product.category.name', read_only=True)
    
    class Meta:
        model = ProductPerformance
        fields = [
            'id', 'product_name', 'product_handle', 'product_image', 'category',
            'total_orders', 'total_quantity_sold', 'total_revenue',
            'order_percentage', 'revenue_percentage',
            'wishlist_count', 'review_count', 'average_rating',
            'updated_at'
        ]
    
    def get_product_image(self, obj):
        request = self.context.get('request')
        if obj.product.image and request:
            return request.build_absolute_uri(obj.product.image.url)
        return None


class RecentOrderSerializer(serializers.ModelSerializer):
    """Serializer for recent orders"""
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(source='user.email', read_only=True)
    product_names = serializers.SerializerMethodField()
    payment_status = serializers.CharField(source='status', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'paystack_checkout_id', 'customer_name', 'customer_email',
            'product_names', 'payment_status', 'amount', 'created_at'
        ]
    
    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_product_names(self, obj):
        """Get comma-separated product names"""
        items = obj.items.select_related('product').all()
        return ', '.join([item.product.name for item in items[:3]])  # Limit to 3


class VendorNotificationSerializer(serializers.ModelSerializer):
    """Serializer for vendor notifications"""
    class Meta:
        model = VendorNotification
        fields = ['id', 'type', 'title', 'message', 'is_read', 'link', 'created_at']


class VendorDashboardOverviewSerializer(serializers.Serializer):
    """Complete dashboard overview"""
    analytics = VendorAnalyticsSerializer(read_only=True)
    sales_trend = VendorSalesRecordSerializer(many=True, read_only=True)
    top_products = ProductPerformanceSerializer(many=True, read_only=True)
    recent_orders = RecentOrderSerializer(many=True, read_only=True)
    notifications = VendorNotificationSerializer(many=True, read_only=True)
    
    # Market share data
    market_share = serializers.DictField(read_only=True)
    
    # Stats cards
    items_sold = serializers.IntegerField(read_only=True)
    shipping_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    processing_count = serializers.IntegerField(read_only=True)


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order information for vendor"""
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(source='user.email', read_only=True)
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'paystack_checkout_id', 'customer_name', 'customer_email',
            'amount', 'currency', 'status', 'created_at', 'items'
        ]
    
    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_items(self, obj):
        """Get order items for this vendor only"""
        vendor = self.context.get('vendor')
        items = obj.items.filter(product__vendor=vendor).select_related('product')
        
        return [{
            'product_id': item.product.id,
            'product_name': item.product.name,
            'product_handle': item.product.handle,
            'quantity': item.quantity,
            'price': float(item.product.price),
            'subtotal': float(item.product.price * item.quantity)
        } for item in items]


class ProductAnalyticsSerializer(serializers.Serializer):
    """Analytics for a specific product"""
    product = serializers.SerializerMethodField()
    performance = ProductPerformanceSerializer(read_only=True)
    sales_by_day = serializers.DictField(read_only=True)
    recent_reviews = serializers.SerializerMethodField()
    stock_status = serializers.DictField(read_only=True)
    
    def get_product(self, obj):
        from stock.serializers import ProductSerializer  # Avoid circular import
        return ProductSerializer(obj, context=self.context).data
    
    def get_recent_reviews(self, obj):
        reviews = Reviews.objects.filter(product=obj).order_by('-created_at')[:5]
        return [{
            'user': review.user.username,
            'rating': review.ratings,
            'review': review.reviews,
            'created_at': review.created_at
        } for review in reviews]