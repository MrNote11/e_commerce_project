from django.db import models
import uuid
from decimal import Decimal
from django.utils import timezone
from vendors.models import VendorProfile
from home.models import User
from cloudinary.models import CloudinaryField
from django_resized import ResizedImageField
from django.utils.text import slugify
from django.core.validators import MinValueValidator
import re

class Category(models.Model):  # Changed to singular
    class StatusChoice(models.TextChoices):
        POLO = "polo"
        TOP = "top"  # Fixed: lowercase for consistency
        SHIRT = "shirt"
        TROUSERS = "trousers"  # Fixed: was "skirt"
    
    name = models.CharField(max_length=50)
    choice = models.CharField(max_length=50, choices=StatusChoice.choices)
    slug = models.SlugField(unique=True, blank=True)
    image = ResizedImageField(size=[900, 900], quality=94, upload_to="product_image", blank=True, null=True)
    
    def __str__(self):
        return self.name 
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Category.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)



class Product(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', '2X Large'),
        ('XXXL', '3X Large'),
    ]
    
    COLOR_CHOICES = [
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('black', 'Black'),
        ('white', 'White'),
        ('gray', 'Gray'),
        ('navy', 'Navy'),
        ('pink', 'Pink'),
        ('purple', 'Purple'),
        ('yellow', 'Yellow'),
        ('orange', 'Orange'),
        ('brown', 'Brown'),
        ('beige', 'Beige'),
        ('multi', 'Multi-color'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="vendor_product")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="category_product", blank=True, null=True)
    name = models.CharField(max_length=50)
    handle = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(
        decimal_places=2, 
        max_digits=12,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    default_price = models.DecimalField(
        decimal_places=2, 
        max_digits=12, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    payment_gateway_price = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(upload_to="product_image", blank=True, null=True)
    price_changed_at = models.DateTimeField(default=timezone.now)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # REQUIRED: Everyone must use product_sizes with height
    product_sizes = models.JSONField(
        default=dict,
        blank=False,
        help_text="REQUIRED: ONE size with height: {'M': {'height': '5.10'}}"
    )
    
    # CHANGED: Now a dictionary to store color quantities
    product_colors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Color quantities: {'red': 5, 'blue': 3, 'black': 2} - max 10 per color"
    )
    
    # available=models.BooleanField(default=True, help_text="Is this product available for sale?")
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['name']),
            models.Index(fields=['default_price']),
            models.Index(fields=['timestamp']),
            # models.Index(fields=['available'])
        ]
        ordering = ['-timestamp']
        
        
    def save(self, *args, **kwargs):
        if not self.handle:
            base_handle = slugify(self.name)
            unique_handle = f"{base_handle}-{uuid.uuid4().hex[:6]}"
            counter = 1
            while Product.objects.filter(handle=unique_handle).exists():
                unique_handle = f"{base_handle}-{uuid.uuid4().hex[:6]}-{counter}"
                counter += 1
            self.handle = unique_handle
        
        if self.price != self.default_price:
            self.default_price = self.price
            self.payment_gateway_price = int((self.price * Decimal('100')).quantize(Decimal('1')))
            self.price_changed_at = timezone.now()
        
        #  FIXED: Proper validation that prevents save
        if self.product_colors and isinstance(self.product_colors, dict):
            for color, quantity in self.product_colors.items():
                if quantity > 10:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(f"Quantity for {color} cannot exceed 10")
        
        # Calculate total stock from color quantities
        if self.product_colors and isinstance(self.product_colors, dict):
            self.stock = sum(quantity for quantity in self.product_colors.values())
        
        super().save(*args, **kwargs)


    @property
    def in_stock(self):
        return self.stock > 0
    
    @property
    def height(self):
        """Get height from the first size in product_sizes"""
        if self.product_sizes and isinstance(self.product_sizes, dict) and len(self.product_sizes) > 0:
            first_size_data = list(self.product_sizes.values())[0]
            if isinstance(first_size_data, dict):
                return first_size_data.get('height', '')
        return ''
    
    @property
    def size(self):
        """Get first size from product_sizes"""
        if self.product_sizes and isinstance(self.product_sizes, dict) and len(self.product_sizes) > 0:
            return list(self.product_sizes.keys())[0]
        return ''
    
    @property
    def available_sizes(self):
        """Get all available sizes with their heights"""
        if self.product_sizes and isinstance(self.product_sizes, dict):
            return [
                {"size": size, "height": data.get('height', '')}
                for size, data in self.product_sizes.items()
            ]
        return []
    
    @property
    def item_subtotal(self):
        return self.price * self.stock


class Cart(models.Model):
    class StatusChoice(models.TextChoices):
        PENDING = "Pending"
        SUCCESSFUL = "Successful"
        CANCELLED = "Cancelled"
        PROCESSING = "Processing"  # Added new status

    cart_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=15, choices=StatusChoice.choices, default=StatusChoice.PENDING)  # Fixed: better field name

    def __str__(self):
        return str(self.cart_id)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_cartitem')
    quantity = models.PositiveIntegerField(default=1)
    
    #  ADD THESE FIELDS to track user's selection
    selected_size = models.CharField(max_length=10, choices=Product.SIZE_CHOICES, blank=True, null=True)
    selected_height = models.CharField(max_length=10, blank=True, null=True)  # Store the specific height for the selected size
    selected_color = models.CharField(max_length=20, choices=Product.COLOR_CHOICES, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def item_subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name} ({self.selected_size}, {self.selected_color}) in cart {self.cart.cart_id}"



class Order(models.Model):
    paystack_checkout_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Paid", "Paid")])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.paystack_checkout_id } - {self.status}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"Order {self.product.name} - {self.order.paystack_checkout_id }"
    

# Newly Added 
class CustomerAddress(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    street = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=13, blank=True, null=True)

    def __str__(self):
        return f"{self.customer.email} - {self.street} - {self.city}"
    
    
class Reviews(models.Model):
    RATING_CHOICES = (
    (1, "1 Bad"),
    (2, "2 Niche"),
    (3, "3 Good"),
    (4, "4 Perfect"),
    (5, "5 Excellent"),
)

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_reviews")
    ratings = models.IntegerField(choices=RATING_CHOICES)
    reviews = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['ratings']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['product']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.ratings}"
    

class ProductRating(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='rating')
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.average_rating} ({self.total_reviews} reviews)"



class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist")
    created = models.DateTimeField(auto_now_add=True) 

    class Meta:
        unique_together = ["user", "product"]

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
    