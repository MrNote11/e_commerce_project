from django.urls import path
from .views import (
    ProductListViews, ProductDetailViews,
    CategoryListViews, CategoryDetailViews,
    CartItemView, ReviewViewSet,
    WishlistViewSet, SearchProductsView,
    ProductRatingViews, CartCountAPIView,
    CartCheckoutAPIView, OrderAPIView,
    OrderDetailAPIView, CartDebugAPIView, 
    CartHealthCheckView,
)
 
urlpatterns = [
    # Product endpoints
    path('products/', ProductListViews.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailViews.as_view(), name='product-detail'),
    
    # Category endpoints
    path('categories/', CategoryListViews.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailViews.as_view(), name='category-detail'),
    
    # Cart endpoints
    path('cart/', CartItemView.as_view(), name='cart'),
    path('cart/<int:cart_item_id>/', CartItemView.as_view(), name='cart-item'),
    path('cart/count/', CartCountAPIView.as_view(), name='cart-count'),
    path('cart/checkout/', CartCheckoutAPIView.as_view(), name='cart-checkout'),
    
    # Order endpoints
    path('orders/', OrderAPIView.as_view(), name='orders'),
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='order-detail'),
    
    # Review endpoints
    path('reviews/', ReviewViewSet.as_view(), name='review-list'),
    path('reviews/<int:pk>/', ReviewViewSet.as_view(), name='review-detail'),
    
    # Wishlist endpoints
    path('wishlist/', WishlistViewSet.as_view(), name='wishlist'),
    
    # Search
    path('search/', SearchProductsView.as_view(), name='search-products'),
    
    # Ratings
    path('products/<int:product_id>/rating/', ProductRatingViews.as_view(), name='product-rating'),

    # Cart debug
    path('cart/debug/', CartDebugAPIView.as_view(), name='cart-debug'),
    path('cart/health/', CartHealthCheckView.as_view(), name='cart_health'),
]  