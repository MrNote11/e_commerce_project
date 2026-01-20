from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import Product, Cart, CartItem, Category, Reviews, Wishlist, Order
from e_commerce.modules.email_utils import send_vendor_verification_email
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from home.serializers import UserSerializerOut
from vendors.serializers import *




class CartItemListSerializer(serializers.ModelSerializer):
    cloth_name = serializers.CharField(source='product.name', read_only=True)
    cloth_price = serializers.DecimalField(source='product.price', read_only=True, max_digits=12, decimal_places=2)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'cloth_name', 'cloth_price', 'product_image', 
            'quantity', 'selected_size', 'selected_height', 'selected_color',
            'item_subtotal', 'created_at'
        ]
        read_only_fields = ['created_at', 'item_subtotal']


class CartItemCreateSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    
    class Meta: 
        model = CartItem
        fields = ['id', 'product', 'quantity', 'selected_size', 'selected_color', 'selected_height']
        read_only_fields = ['id']
    
    def validate(self, attrs):
        product = attrs['product']
        selected_size = attrs.get('selected_size')
        selected_height = attrs.get('selected_height')
        selected_color = attrs.get('selected_color')
        quantity = attrs.get('quantity', 1)

        if not product:
            raise serializers.ValidationError("Product is required.")
        
        if not quantity or quantity <= 0:
            raise serializers.ValidationError("Please Input a correct amount.")
        
        # Validate selected size exists in product
        if selected_size and selected_size not in product.product_sizes:
            raise serializers.ValidationError({
                "selected_size": f"Size {selected_size} is not available for this product. Available sizes: {', '.join(product.product_sizes.keys())}"
            })
        
        # Validate height if size is selected
        if selected_size and selected_height:
            size_data = product.product_sizes.get(selected_size)
            
            if not size_data:
                raise serializers.ValidationError("Selected size is required for this product")
            
            height_in_db = size_data.get("height")
            
            if height_in_db is None:
                raise ValidationError("This size has no height configuration")
            
            # Convert safely
            try:
                user_height = Decimal(str(selected_height))
                allowed_height = Decimal(str(height_in_db))
            except (InvalidOperation, TypeError):
                raise ValidationError("Height must be a valid decimal number")
            
            # Compare
            if user_height != allowed_height:
                raise ValidationError("Selected height is not valid for this size")
        
        # Validate selected color exists in product
        if selected_color and selected_color not in product.product_colors:
            raise serializers.ValidationError({
                "selected_color": f"Color {selected_color} is not available for this product. Available colors: {', '.join(product.product_colors.keys())}"
            })
        
        # Validate color has sufficient stock
        if selected_color:
            color_quantity = product.product_colors.get(selected_color, 0)
            if color_quantity < quantity:
                raise serializers.ValidationError({
                    "quantity": f"Only {color_quantity} items available in {selected_color}. You requested {quantity}."
                })
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        
        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=user)
        
        product = validated_data['product']
        selected_size = validated_data.get('selected_size')
        selected_color = validated_data.get('selected_color')
        selected_height = validated_data.get('selected_height')
        quantity = validated_data['quantity']
        
        # Check if same product with same size/color already exists in cart
        cart_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            selected_size=selected_size,
            selected_color=selected_color,
            selected_height=selected_height  # Also check height
        ).first()
        
        if cart_item:
            # Calculate new total quantity
            new_quantity = cart_item.quantity + quantity
            
            # Re-validate stock with new total quantity
            if selected_color:
                color_quantity = product.product_colors.get(selected_color, 0)
                if color_quantity < new_quantity:
                    raise serializers.ValidationError({
                        "quantity": f"Only {color_quantity} items available in {selected_color}. Your cart already has {cart_item.quantity} and you can't add {quantity} more."
                    })
            
            # Update quantity if item already exists
            cart_item.quantity = new_quantity
            cart_item.save()
            
        else:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                selected_size=selected_size,
                selected_height=selected_height,
                selected_color=selected_color,
                quantity=quantity
            )
        
        return cart_item


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemListSerializer(many=True, read_only=True)
    cart_total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['cart_id', 'cart_items', 'cart_total', 'items_count', 'user', 'status', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
        
    def get_cart_total(self, obj):
        items = obj.cart_items.all()
        return sum(item.item_subtotal for item in items)
    
    def get_items_count(self, obj):
        return obj.cart_items.count()


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializerOut(read_only=True)
    class Meta:
        model = Order
        fields = ['cart_id', 'user', 'status', 'created_at', 'updated_at']
        read_only_fields = ['cart_id', 'user', 'status', 'created_at', 'updated_at']
        
class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders from cart"""
    cart_id = serializers.UUIDField(help_text="Cart ID to checkout")
    shipping_address = serializers.CharField(
        max_length=500,
        help_text="Shipping address"
    )
    phone = serializers.CharField(
        max_length=15,
        help_text="Phone number for delivery"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional order notes"
    )
    
    def validate_cart_id(self, value):
        request = self.context.get('request')
        
        try:
            cart = Cart.objects.get(cart_id=value, user=request.user)
            
            if not cart.cart_items.exists():
                raise serializers.ValidationError("Cart is empty")
            
            if cart.status == Cart.StatusChoice.SUCCESSFUL:
                raise serializers.ValidationError("This cart has already been checked out")
            
            return value
            
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart not found")
        
class ReviewSerializer(serializers.ModelSerializer):
   
    # product = ProductSerializer(read_only=True)
    class Meta:
        model = Reviews
        fields = ['id', 'product', 'ratings', 'reviews', 'updated_at']
        read_only_fields = ['updated_at', 'id']
        
        
    def validate_ratings(self, value):
        if value not in dict(Reviews.RATING_CHOICES).keys():
            raise serializers.ValidationError("Invalid rating choice.")
        
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Ratings must be between 1 and 5.")
        return value
    
    
    def validate(self, attrs):
        product = attrs.get('product')
        user = self.context['request'].user
        # Check if user has already reviewed this product
        if Reviews.objects.filter(product=product, user=user).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        
        
        
        return attrs
    
    def to_representation(self, instance):
        return super().to_representation(instance)
        

class WishlistSerializer(serializers.ModelSerializer):
    # user = UserSerializerOut(read_only=True)
    product = ProductSerializer(read_only=True)
    class Meta:
        model = Wishlist 
        fields = ["id", "product", "created"]
        read_only_fields = ["id", "created"]

