# stock/filters.py (add to your existing filters)
import django_filters
from django import forms
from .models import Payment, PaystackTransaction
from stock.models import Order, Cart, Product, Category

class PaymentFilter(django_filters.FilterSet):
    """Filter for Payment model"""
    PAYMENT_TYPE_CHOICES = [
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash on Delivery'),
    ]
    
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
        ('Cancelled', 'Cancelled'),
    ]

    payment_method = django_filters.ChoiceFilter(
        choices=PAYMENT_TYPE_CHOICES,
        field_name="payment_method",
        lookup_expr="iexact",
        empty_label="Any",
    )

    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
        field_name="status",
        lookup_expr="iexact",
        empty_label="Any",
    )

    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Date From",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Date To",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    min_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="gte",
        label="Min Amount"
    )

    max_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="lte",
        label="Max Amount"
    )

    order = django_filters.ModelChoiceFilter(
        queryset=Order.objects.all(),
        field_name="order",
        label="Order"
    )

    class Meta:
        model = Payment
        fields = ("payment_method", "status", "start_date", "end_date", "min_amount", "max_amount", "order")


class PaystackTransactionFilter(django_filters.FilterSet):
    """Filter for PaystackTransaction model"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]

    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
        field_name="status",
        lookup_expr="iexact",
        empty_label="Any",
    )

    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Date From",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Date To",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    min_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="gte",
        label="Min Amount"
    )

    max_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="lte",
        label="Max Amount"
    )

    class Meta:
        model = PaystackTransaction
        fields = ("status", "start_date", "end_date", "min_amount", "max_amount")


class RevenueAnalyticsFilter(django_filters.FilterSet):
    """Filter for revenue analytics"""
    date_range = django_filters.ChoiceFilter(
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_7_days', 'Last 7 Days'),
            ('last_30_days', 'Last 30 Days'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range')
        ],
        method='filter_date_range',
        empty_label="Select Date Range"
    )
    
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        method='filter_by_category',
        label="Product Category"
    )
    
    payment_method = django_filters.ChoiceFilter(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        field_name="payment_method",
        lookup_expr="iexact",
        empty_label="All Payment Methods"
    )

    status = django_filters.ChoiceFilter(
        choices=Payment.STATUS_CHOICES,
        field_name="status",
        lookup_expr="iexact",
        empty_label="All Statuses"
    )
    
    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Custom Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Custom End Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    min_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="gte",
        label="Min Amount"
    )

    max_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="lte",
        label="Max Amount"
    )
    
    def filter_date_range(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        if value == 'today':
            return queryset.filter(created_at__date=now.date())
        elif value == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        elif value == 'last_7_days':
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        elif value == 'last_30_days':
            return queryset.filter(created_at__gte=now - timedelta(days=30))
        elif value == 'this_month':
            return queryset.filter(
                created_at__year=now.year,
                created_at__month=now.month
            )
        elif value == 'last_month':
            last_month = now.month - 1 if now.month > 1 else 12
            year = now.year if now.month > 1 else now.year - 1
            return queryset.filter(
                created_at__year=year,
                created_at__month=last_month
            )
        elif value == 'this_year':
            return queryset.filter(created_at__year=now.year)
        return queryset
    
    def filter_by_category(self, queryset, name, value):
        """Filter payments by product category"""
        if value:
            return queryset.filter(
                order__items__product__category=value
            ).distinct()
        return queryset

    class Meta:
        model = Payment
        fields = ["date_range", "category", "payment_method", "start_date", "status", "end_date", "min_amount", "max_amount"]