import django_filters
from stock.models import Product, Order, CartItem, Category
from rest_framework import filters

class InStockFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(stock__gt=0)


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    category = django_filters.CharFilter(field_name='category__slug')

    class Meta:
        model = Product
        fields = {
            'name': ['iexact', 'icontains'],
            'price': ['exact', 'lt', 'gt', 'range']
        }

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset.filter(stock=0)
    

class OrderFilter(django_filters.FilterSet):
    created_at = django_filters.DateFilter(field_name='created_at__date')
    class Meta:
        model = Order
        fields = {
            'status': ['exact'],
            'created_at': ['lt', 'gt', 'exact'],
            'amount': ['exact', 'lt', 'gt', 'range']
        }


class CartItemFilter(django_filters.FilterSet):
    created_at = django_filters.DateFilter(field_name='created_at__date')
    class Meta:
        model = CartItem
        fields = {
            'created_at': ['lt', 'gt', 'exact'],
            'selected_size': ['iexact'],
            'selected_color': ['iexact'],
            'selected_height': ['iexact'],
            'quantity': ['exact', 'lt', 'gt', 'range']
        }


class CategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    choice   = django_filters.MultipleChoiceFilter(choices=Category.StatusChoice.choices)
    class Meta:
        model = Category
        fields = {
            'name': ['iexact', 'icontains'],
            'slug': ['iexact', 'icontains'],
            'choice': ['exact', 'icontains', 'in']
        }
        

