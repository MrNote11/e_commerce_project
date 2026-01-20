# views.py
import logging
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .models import VendorProfile, VendorAnalytics, VendorSalesRecord, ProductPerformance, VendorNotification
from .serializers import (
    VendorProfileSerializer, VendorCreateSerializer, ProductSerializer,
    VendorAnalyticsSerializer, ProductPerformanceSerializer, VendorNotificationSerializer,
    RecentOrderSerializer, OrderDetailSerializer, ProductAnalyticsSerializer
)
from .permission import IsVendor, IsApprovedVendor
from e_commerce.modules.utils import incoming_request_checks, api_response
from e_commerce.modules.paginations import CustomPagination
from stock.models import Order, OrderItem, Product, Cart, Reviews
from stock.filters import ProductFilter

logger = logging.getLogger(__name__)


class VendorProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vendor profiles.
    """
    permission_classes = [IsAuthenticated]  # Only require authentication
    serializer_class = VendorProfileSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        """
        Custom permissions for different actions.
        """
        if self.action == 'register':
            # Allow any authenticated user to register as vendor
            return [IsAuthenticated()]
        elif self.action in ['my_profile', 'update_profile', 'delete_profile']:
            # For profile management, user must be a vendor
            return [IsAuthenticated(), IsVendor()]
        elif self.action in ['create', 'list', 'retrieve', 'update', 'partial_update', 'destroy']:
            # CRUD operations only for admin users
            return [IsAuthenticated(), IsAuthenticated().has_permission]  # Adjust as needed
        return super().get_permissions()
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get_queryset(self):
        """
        Get queryset based on user permissions.
        """
        # Admin users can see all vendors, regular users only see their own
        if self.request.user.is_staff or self.request.user.is_superuser:
            return VendorProfile.objects.all()
        elif hasattr(self.request.user, 'vendor_profile'):
            return VendorProfile.objects.filter(user=self.request.user)
        return VendorProfile.objects.none()
    
    @swagger_auto_schema(
        request_body=VendorCreateSerializer,
        responses={201: openapi.Response(description="Vendor registered successfully")}
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request):
        """
        Register as a new vendor (for authenticated users who aren't vendors yet).
        """
        # Check if user is already a vendor
        if hasattr(request.user, 'vendor_profile'):
            return Response(
                api_response(
                    message="You are already registered as a vendor",
                    status=False
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = VendorCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            vendor = serializer.save()
            return Response(
                api_response(
                    message="Vendor registration submitted for approval",
                    status=True,
                    data={
                        "vendorprofile": VendorProfileSerializer(vendor).data,
                        "approval": "Email approval shall be sent within a day"
                    }
                ),
                status=status.HTTP_201_CREATED
            )
        return Response(
            api_response(
                message="Validation failed",
                status=False,
                data={"errors": serializer.errors}
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVendor])
    def my_profile(self, request):
        """
        Get current vendor's profile (requires user to be a vendor).
        """
        vendor_profile = request.user.vendor_profile
        if vendor_profile.is_approved is False:
            return Response(
                api_response(
                    message="Vendor profile is not approved yet",
                    status=False
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(vendor_profile)
        return Response(
            api_response(
                message="Vendor profile retrieved",
                status=True,
                data=serializer.data
            )
        )
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated, IsVendor])
    def update_profile(self, request):
        """
        Update vendor profile (requires user to be a vendor).
        """
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        vendor_profile = request.user.vendor_profile
        if vendor_profile.is_approved is False:
            return Response(
                api_response(
                    message="Vendor profile is not approved yet",
                    status=False
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VendorProfileSerializer(vendor_profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                api_response(
                    message="Vendor profile updated successfully",
                    status=True,
                    data=serializer.data
                )
            )
        return Response(
            api_response(
                message="Profile update failed",
                status=False,
                data={"errors": serializer.errors}
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['delete'], permission_classes=[IsAuthenticated, IsVendor])
    def delete_profile(self, request):
        """
        Delete vendor profile (requires user to be a vendor).
        """
        vendor_profile = request.user.vendor_profile
        if vendor_profile.is_approved is False:
            return Response(
                api_response(
                    message="Vendor profile is not approved yet",
                    status=False
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update user role
        user = vendor_profile.user
        user.role = 'CUSTOMER'  # Assuming User model has a role field
        user.save()
        
        vendor_profile.delete()
        
        return Response(
            api_response(
                message="Vendor profile deleted successfully",
                status=True
            )
        )


class ProductViewSet(viewsets.ModelViewSet, CustomPagination):
    """
    ViewSet for managing vendor products.
    """
    permission_classes = [IsAuthenticated, IsVendor, IsApprovedVendor]
    serializer_class = ProductSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    
    @swagger_auto_schema(
        request_body=ProductSerializer,
        responses={201: openapi.Response(description="Product created successfully")}
    )
    def get_queryset(self):
        """
        Get products belonging to the current vendor.
        """
        return Product.objects.filter(vendor__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new product.
        """
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(
                api_response(message=data, status=False),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = self.get_serializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                api_response(
                    message="Product created successfully",
                    status=True,
                    data=serializer.data
                ),
                status=status.HTTP_201_CREATED
            )
        return Response(
            api_response(
                message="Product creation failed",
                status=False,
                data={"errors": serializer.errors}
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        """
        GET /products/ - List all products for the vendor.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Simple in_stock filter based on total stock
            in_stock = request.query_params.get('in_stock')
            if in_stock and in_stock.lower() == 'true':
                queryset = queryset.filter(stock__gt=0)
            elif in_stock and in_stock.lower() == 'false':
                queryset = queryset.filter(
                    Q(stock=0) |
                    Q(color_quantities__isnull=True) |
                    Q(color_quantities__regex=r'^{.*"quantity"\s*:\s*0.*}$')
                )
            
            paginated_queryset = self.paginate_queryset(queryset)
            serializer = self.get_serializer(paginated_queryset, many=True)
            
            if paginated_queryset:
                return self.get_paginated_response(serializer.data)
            return Response(
                api_response(
                    message="Products retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            )
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve products",
                    status=False,
                    data={"error": str(e)}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /products/{id}/ - Retrieve a specific product.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                api_response(
                    message="Product retrieved successfully",
                    status=True,
                    data=serializer.data
                )
            )
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving product: {str(e)}")
            return Response(
                api_response(
                    message="Failed to retrieve product",
                    status=False,
                    data={"error": str(e)}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        PUT /products/{id}/ - Full update of a product.
        """
        try:
            instance = self.get_object()
            status_, data = incoming_request_checks(request)
            
            if not status_:
                return Response(
                    api_response(message=data, status=False),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            serializer = self.get_serializer(instance, data=data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(
                    api_response(
                        message="Product updated successfully",
                        status=True,
                        data=serializer.data
                    )
                )
            
            return Response(
                api_response(
                    message="Failed to update product",
                    status=False,
                    data={"errors": serializer.errors}
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            return Response(
                api_response(
                    message="Failed to update product",
                    status=False,
                    data={"error": str(e)}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /products/{id}/ - Partial update of a product.
        """
        try:
            instance = self.get_object()
            status_, data = incoming_request_checks(request)
            
            if not status_:
                return Response(
                    api_response(message=data, status=False),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            serializer = self.get_serializer(instance, data=data, partial=True, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(
                    api_response(
                        message="Product updated successfully",
                        status=True,
                        data=serializer.data
                    )
                )
            
            return Response(
                api_response(
                    message="Failed to update product",
                    status=False,
                    data={"errors": serializer.errors}
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error partially updating product: {str(e)}")
            return Response(
                api_response(
                    message="Failed to update product",
                    status=False,
                    data={"error": str(e)}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /products/{id}/ - Delete a product.
        """
        try:
            instance = self.get_object()
            product_id = instance.id
            product_name = instance.name
            
            instance.delete()
            
            return Response(
                api_response(
                    message=f"Product '{product_name}' deleted successfully",
                    status=True,
                    data={"deleted_product_id": product_id}
                )
            )
            
        except Product.DoesNotExist:
            return Response(
                api_response(
                    message="Product not found",
                    status=False,
                    data=None
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}")
            return Response(
                api_response(
                    message="Failed to delete product",
                    status=False,
                    data={"error": str(e)}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VendorDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for vendor dashboard operations.
    """
    permission_classes = [IsAuthenticated, IsVendor]
    
    def get_vendor(self):
        """
        Get the current user's vendor profile.
        """
        return self.request.user.vendor_profile
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Get complete dashboard overview with all metrics.
        GET /api/vendor/dashboard/overview/
        """
        vendor = self.get_vendor()
        today = timezone.now().date()
        
        # Update analytics
        analytics = VendorAnalytics.calculate_for_vendor(vendor, today)
        
        # Get sales trend for last 30 days
        thirty_days_ago = today - timedelta(days=30)
        sales_records = self._get_sales_trend(vendor, thirty_days_ago, today)
        
        # Get top 7 products
        top_products = ProductPerformance.objects.filter(
            product__vendor=vendor
        ).order_by('-total_revenue')[:7]
        
        # Get recent 10 orders
        recent_orders = Order.objects.filter(
            items__product__vendor=vendor
        ).distinct().order_by('-created_at')[:10]
        
        # Get unread notifications
        notifications = VendorNotification.objects.filter(
            vendor=vendor,
            is_read=False
        )[:5]
        
        # Calculate additional metrics
        items_sold = OrderItem.objects.filter(
            product__vendor=vendor,
            order__status='Paid'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        shipping_amount = Decimal('365.53')  # Mock - implement your shipping logic
        
        processing_orders = Order.objects.filter(
            items__product__vendor=vendor,
            status='Pending'
        ).distinct().count()
        
        # Market share calculation (mock data - adjust based on your needs)
        market_share = {
            'categories': ['Marketing', 'Sales', 'Dev', 'Support', 'Tech', 'Admin'],
            'allocated_budget': [80, 90, 70, 60, 85, 80],
            'actual_spending': [70, 95, 90, 50, 65, 75]
        }
        
        data = {
            'analytics': VendorAnalyticsSerializer(analytics).data,
            'sales_trend': sales_records,
            'top_products': ProductPerformanceSerializer(
                top_products, many=True, context={'request': request}
            ).data,
            'recent_orders': RecentOrderSerializer(
                recent_orders, many=True
            ).data,
            'notifications': VendorNotificationSerializer(
                notifications, many=True
            ).data,
            'market_share': market_share,
            'items_sold': items_sold,
            'shipping_amount': shipping_amount,
            'processing_count': processing_orders
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Get detailed analytics.
        GET /api/vendor/dashboard/analytics/?period=week|month|year
        """
        vendor = self.get_vendor()
        period = request.query_params.get('period', 'week')
        
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=7)
        
        # Get or create analytics
        analytics = VendorAnalytics.calculate_for_vendor(vendor, today)
        
        # Get sales trend
        sales_trend = self._get_sales_trend(vendor, start_date, today)
        
        # Get product performance
        product_performance = ProductPerformance.objects.filter(
            product__vendor=vendor
        ).order_by('-total_revenue')[:10]
        
        data = {
            'analytics': VendorAnalyticsSerializer(analytics).data,
            'sales_trend': sales_trend,
            'product_performance': ProductPerformanceSerializer(
                product_performance, many=True, context={'request': request}
            ).data,
            'period': period,
            'start_date': start_date,
            'end_date': today
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def orders(self, request):
        """
        Get vendor orders with filtering.
        GET /api/vendor/dashboard/orders/?status=Paid&page=1&page_size=20
        """
        vendor = self.get_vendor()
        
        # Get query parameters
        order_status = request.query_params.get('status', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Base query
        orders = Order.objects.filter(
            items__product__vendor=vendor
        ).distinct().order_by('-created_at')
        
        # Filter by status
        if order_status:
            orders = orders.filter(status=order_status)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        total_count = orders.count()
        
        orders_page = orders[start:end]
        
        data = {
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': OrderDetailSerializer(
                orders_page, many=True, context={'vendor': vendor}
            ).data
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """
        Get vendor products with analytics.
        GET /api/vendor/dashboard/products/?sort_by=revenue|orders|stock
        """
        vendor = self.get_vendor()
        sort_by = request.query_params.get('sort_by', 'revenue')
        
        products = Product.objects.filter(vendor=vendor)
        
        # Update performance for all products
        for product in products:
            ProductPerformance.update_for_product(product)
        
        # Get performance records
        if sort_by == 'revenue':
            performances = ProductPerformance.objects.filter(
                product__vendor=vendor
            ).order_by('-total_revenue')
        elif sort_by == 'orders':
            performances = ProductPerformance.objects.filter(
                product__vendor=vendor
            ).order_by('-total_orders')
        elif sort_by == 'stock':
            performances = ProductPerformance.objects.filter(
                product__vendor=vendor
            ).order_by('product__stock')
        else:
            performances = ProductPerformance.objects.filter(
                product__vendor=vendor
            ).order_by('-total_revenue')
        
        data = ProductPerformanceSerializer(
            performances, many=True, context={'request': request}
        ).data
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='product-analytics')
    def product_analytics(self, request, pk=None):
        """
        Get detailed analytics for a specific product.
        GET /api/vendor/dashboard/{product_id}/product-analytics/
        """
        vendor = self.get_vendor()
        
        try:
            product = Product.objects.get(pk=pk, vendor=vendor)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update performance
        performance = ProductPerformance.update_for_product(product)
        
        # Get sales by day (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        daily_sales = OrderItem.objects.filter(
            product=product,
            order__status='Paid',
            order__created_at__date__gte=thirty_days_ago
        ).values('order__created_at__date').annotate(
            quantity=Sum('quantity'),
            revenue=Sum(F('quantity') * F('product__price'))
        ).order_by('order__created_at__date')
        
        sales_by_day = {
            str(item['order__created_at__date']): {
                'quantity': item['quantity'],
                'revenue': float(item['revenue'])
            }
            for item in daily_sales
        }
        
        # Stock status
        stock_status = {
            'current_stock': product.stock,
            'is_low_stock': product.stock <= 5 and product.stock > 0,
            'is_out_of_stock': product.stock == 0,
            'colors': product.product_colors if product.product_colors else {}
        }
        
        data = {
            'performance': ProductPerformanceSerializer(performance).data,
            'sales_by_day': sales_by_day,
            'stock_status': stock_status,
            'recent_reviews': self._get_recent_reviews(product)
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def notifications(self, request):
        """
        Get vendor notifications.
        GET /api/vendor/dashboard/notifications/?unread_only=true
        """
        vendor = self.get_vendor()
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        
        notifications = VendorNotification.objects.filter(vendor=vendor)
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        notifications = notifications.order_by('-created_at')[:20]
        
        data = VendorNotificationSerializer(notifications, many=True).data
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='mark-notification-read')
    def mark_notification_read(self, request, pk=None):
        """
        Mark a notification as read.
        POST /api/vendor/dashboard/{notification_id}/mark-notification-read/
        """
        vendor = self.get_vendor()
        
        try:
            notification = VendorNotification.objects.get(pk=pk, vendor=vendor)
            notification.is_read = True
            notification.save()
            
            return Response(
                {'message': 'Notification marked as read'},
                status=status.HTTP_200_OK
            )
        except VendorNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], url_path='mark-all-notifications-read')
    def mark_all_notifications_read(self, request):
        """
        Mark all notifications as read.
        POST /api/vendor/dashboard/mark-all-notifications-read/
        """
        vendor = self.get_vendor()
        
        VendorNotification.objects.filter(
            vendor=vendor,
            is_read=False
        ).update(is_read=True)
        
        return Response(
            {'message': 'All notifications marked as read'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def customer_insights(self, request):
        """
        Get customer insights and trends.
        GET /api/vendor/dashboard/customer-insights/
        """
        vendor = self.get_vendor()
        
        # Get customer orders
        orders = Order.objects.filter(
            items__product__vendor=vendor,
            status='Paid'
        ).distinct()
        
        # Top customers by order value
        top_customers = orders.values(
            'user__id', 'user__email', 'user__first_name', 'user__last_name'
        ).annotate(
            total_spent=Sum('amount'),
            order_count=Count('id')
        ).order_by('-total_spent')[:10]
        
        # Customer retention
        total_customers = orders.values('user').distinct().count()
        returning_customers = orders.values('user').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count()
        
        retention_rate = (returning_customers / total_customers * 100) if total_customers > 0 else 0
        
        data = {
            'top_customers': list(top_customers),
            'total_customers': total_customers,
            'returning_customers': returning_customers,
            'retention_rate': round(retention_rate, 2),
            'new_customers_this_month': self._get_new_customers_this_month(vendor)
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    # Helper methods
    def _get_sales_trend(self, vendor, start_date, end_date):
        """
        Get sales trend data for date range.
        """
        sales_data = []
        current_date = start_date
        
        while current_date <= end_date:
            # Get or create sales record
            record, created = VendorSalesRecord.objects.get_or_create(
                vendor=vendor,
                date=current_date
            )
            
            if created:
                # Calculate metrics for this date
                daily_orders = Order.objects.filter(
                    items__product__vendor=vendor,
                    status='Paid',
                    created_at__date=current_date
                ).distinct()
                
                record.orders_count = daily_orders.count()
                record.revenue = daily_orders.aggregate(
                    total=Sum('amount')
                )['total'] or 0
                
                # Calculate new vs returning customers
                customer_ids = daily_orders.values_list('user_id', flat=True)
                
                for customer_id in customer_ids:
                    previous_orders = Order.objects.filter(
                        items__product__vendor=vendor,
                        user_id=customer_id,
                        created_at__date__lt=current_date
                    ).exists()
                    
                    if previous_orders:
                        record.returning_customers += 1
                    else:
                        record.new_customers += 1
                
                record.save()
            
            sales_data.append({
                'date': str(current_date),
                'new_customers': record.new_customers,
                'returning_customers': record.returning_customers,
                'orders_count': record.orders_count,
                'revenue': float(record.revenue)
            })
            
            current_date += timedelta(days=1)
        
        return sales_data
    
    def _get_recent_reviews(self, product):
        """
        Get recent reviews for a product.
        """
        reviews = Reviews.objects.filter(
            product=product
        ).order_by('-created_at')[:5]
        
        return [{
            'user': review.user.username,
            'rating': review.ratings,
            'review': review.reviews,
            'created_at': review.created_at.isoformat()
        } for review in reviews]
    
    def _get_new_customers_this_month(self, vendor):
        """
        Get count of new customers this month.
        """
        month_start = timezone.now().date().replace(day=1)
        
        # Get all customer IDs who ordered this month
        current_month_customers = set(
            Order.objects.filter(
                items__product__vendor=vendor,
                created_at__date__gte=month_start
            ).values_list('user_id', flat=True)
        )
        
        # Check which ones are new (no previous orders)
        new_count = 0
        for customer_id in current_month_customers:
            previous_orders = Order.objects.filter(
                items__product__vendor=vendor,
                user_id=customer_id,
                created_at__date__lt=month_start
            ).exists()
            
            if not previous_orders:
                new_count += 1
        
        return new_count