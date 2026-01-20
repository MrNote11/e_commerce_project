from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'vendors'

router = DefaultRouter()
router.register(r'vendor', views.VendorProfileViewSet, basename='vendor')
router.register(r'vendor-product', views.ProductViewSet, basename='product')
router.register(r'venndor-dashboard', views.VendorDashboardViewSet, basename='dashboard')
# router.register(r'cloth-descriptions', views.ProductViewSet, basename='products')
# router.register(r'shelves', views.ShelfViewSet, basename='shelf')
# router.register(r'shelves/admin', views.AdminShelfViewSet, basename='admin-shelf')

urlpatterns = [
    path('', include(router.urls)),
]