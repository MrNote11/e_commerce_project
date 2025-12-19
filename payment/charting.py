# stock/charting.py
import plotly.express as px
import plotly.graph_objects as go
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json
from .models import Payment, PaystackTransaction, Order
from stock.models import Cart, Product, Category

def plot_revenue_over_time(qs, timeframe='day'):
    """
    Plot revenue over time
    
    Args:
        qs: Payment queryset
        timeframe: 'day', 'week', 'month', 'year'
    """
    if timeframe == 'day':
        date_format = '%Y-%m-%d'
        group_by = 'day'
    elif timeframe == 'week':
        date_format = '%Y-W%W'
        group_by = 'week'
    elif timeframe == 'month':
        date_format = '%Y-%m'
        group_by = 'month'
    else:  # year
        date_format = '%Y'
        group_by = 'year'
    
    # Aggregate data
    if group_by == 'day':
        revenue_data = qs.extra(
            {'date': "date(created_at)"}
        ).values('date').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('date')
        
        x_vals = [item['date'].strftime(date_format) for item in revenue_data]
        y_vals = [float(item['total']) for item in revenue_data]
        
    elif group_by == 'week':
        revenue_data = qs.extra(
            {'week': "strftime('%Y-W%W', created_at)"}
        ).values('week').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('week')
        
        x_vals = [item['week'] for item in revenue_data]
        y_vals = [float(item['total']) for item in revenue_data]
        
    elif group_by == 'month':
        from django.db.models.functions import TruncMonth
        revenue_data = qs.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        x_vals = [item['month'].strftime(date_format) for item in revenue_data]
        y_vals = [float(item['total']) for item in revenue_data]
    
    fig = px.line(
        x=x_vals,
        y=y_vals,
        title=f'Revenue Over Time ({timeframe.capitalize()}ly)',
        labels={'x': 'Date', 'y': 'Revenue (₦)'}
    )
    
    return fig


def plot_payment_method_distribution(qs):
    """Plot distribution of payment methods"""
    method_data = qs.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    labels = [item['payment_method'].title() for item in method_data]
    values = [float(item['total']) for item in method_data]
    
    fig = px.pie(
        values=values,
        names=labels,
        title='Payment Method Distribution',
        hole=0.3
    )
    
    return fig


def plot_payment_status_distribution(qs):
    """Plot distribution of payment statuses"""
    status_data = qs.values('status').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    labels = [item['status'] for item in status_data]
    values = [item['count'] for item in status_data]
    
    # Create a color map for statuses
    color_map = {
        'Paid': 'green',
        'Pending': 'yellow',
        'Failed': 'red',
        'Cancelled': 'gray'
    }
    
    colors = [color_map.get(status, 'blue') for status in labels]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        marker=dict(colors=colors)
    )])
    
    fig.update_layout(title_text='Payment Status Distribution')
    
    return fig


def plot_category_revenue(qs):
    """Plot revenue by product category"""
    # Get payments with orders and products
    category_data = Category.objects.annotate(
        total_revenue=Sum('category_product__orderitem__order__payment_record__amount',
                         filter=Q(category_product__orderitem__order__payment_record__in=qs)),
        order_count=Count('category_product__orderitem__order',
                         filter=Q(category_product__orderitem__order__payment_record__in=qs),
                         distinct=True)
    ).filter(total_revenue__gt=0).order_by('-total_revenue')
    
    categories = [cat.name for cat in category_data]
    revenues = [float(cat.total_revenue or 0) for cat in category_data]
    
    fig = px.bar(
        x=categories,
        y=revenues,
        title='Revenue by Product Category',
        labels={'x': 'Category', 'y': 'Revenue (₦)'},
        text=revenues
    )
    
    fig.update_traces(texttemplate='₦%{text:,.2f}', textposition='outside')
    
    return fig


def plot_top_products(qs, limit=10):
    """Plot top selling products by revenue"""
    product_data = Product.objects.annotate(
        total_revenue=Sum('orderitem__order__payment_record__amount',
                         filter=Q(orderitem__order__payment_record__in=qs)),
        total_quantity=Sum('orderitem__quantity',
                          filter=Q(orderitem__order__payment_record__in=qs)),
        order_count=Count('orderitem__order',
                         filter=Q(orderitem__order__payment_record__in=qs),
                         distinct=True)
    ).filter(total_revenue__gt=0).order_by('-total_revenue')[:limit]
    
    product_names = [product.name[:20] + '...' if len(product.name) > 20 else product.name 
                    for product in product_data]
    revenues = [float(product.total_revenue or 0) for product in product_data]
    
    fig = px.bar(
        x=revenues,
        y=product_names,
        orientation='h',
        title=f'Top {limit} Products by Revenue',
        labels={'x': 'Revenue (₦)', 'y': 'Product'},
        text=revenues
    )
    
    fig.update_traces(texttemplate='₦%{text:,.2f}', textposition='outside')
    
    return fig


def plot_daily_transaction_volume(qs):
    """Plot daily transaction volume"""
    # Last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_data = qs.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        {'day': "date(created_at)"}
    ).values('day').annotate(
        count=Count('id'),
        amount=Sum('amount')
    ).order_by('day')
    
    dates = [item['day'].strftime('%Y-%m-%d') for item in daily_data]
    counts = [item['count'] for item in daily_data]
    amounts = [float(item['amount'] or 0) for item in daily_data]
    
    fig = go.Figure()
    
    # Add transaction count trace
    fig.add_trace(go.Bar(
        x=dates,
        y=counts,
        name='Transaction Count',
        marker_color='lightblue',
        yaxis='y'
    ))
    
    # Add revenue trace (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=dates,
        y=amounts,
        name='Revenue (₦)',
        marker_color='darkgreen',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Daily Transaction Volume & Revenue (Last 30 Days)',
        xaxis_title='Date',
        yaxis_title='Transaction Count',
        yaxis2=dict(
            title='Revenue (₦)',
            overlaying='y',
            side='right'
        ),
        barmode='group'
    )
    
    return fig


def plot_conversion_funnel(qs):
    """Plot payment conversion funnel"""
    # Calculate conversion funnel metrics
    total_carts = Cart.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    carts_with_payment_attempt = Cart.objects.filter(
        payment_records__isnull=False,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).distinct().count()
    
    successful_payments = qs.filter(
        status='Paid',
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Calculate conversion rates
    cart_to_payment_rate = (carts_with_payment_attempt / total_carts * 100) if total_carts > 0 else 0
    payment_success_rate = (successful_payments / carts_with_payment_attempt * 100) if carts_with_payment_attempt > 0 else 0
    overall_conversion_rate = (successful_payments / total_carts * 100) if total_carts > 0 else 0
    
    stages = ['Cart Created', 'Payment Attempted', 'Payment Successful']
    values = [total_carts, carts_with_payment_attempt, successful_payments]
    rates = [100, cart_to_payment_rate, payment_success_rate]
    
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        marker=dict(
            color=['lightblue', 'lightgreen', 'green']
        )
    ))
    
    fig.update_layout(
        title='Payment Conversion Funnel (Last 30 Days)',
        showlegend=False
    )
    
    return fig


def plot_average_order_value_trend(qs):
    """Plot average order value trend"""
    # Calculate AOV by day for last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_aov = qs.filter(
        status='Paid',
        created_at__gte=thirty_days_ago
    ).extra(
        {'day': "date(created_at)"}
    ).values('day').annotate(
        avg_amount=Avg('amount'),
        count=Count('id')
    ).order_by('day')
    
    dates = [item['day'].strftime('%Y-%m-%d') for item in daily_aov]
    avg_amounts = [float(item['avg_amount'] or 0) for item in daily_aov]
    counts = [item['count'] for item in daily_aov]
    
    fig = go.Figure()
    
    # Add AOV line
    fig.add_trace(go.Scatter(
        x=dates,
        y=avg_amounts,
        name='Average Order Value',
        mode='lines+markers',
        marker_color='blue'
    ))
    
    # Add transaction count bars (secondary y-axis)
    fig.add_trace(go.Bar(
        x=dates,
        y=counts,
        name='Transaction Count',
        marker_color='lightblue',
        opacity=0.5,
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Average Order Value Trend (Last 30 Days)',
        xaxis_title='Date',
        yaxis_title='Average Order Value (₦)',
        yaxis2=dict(
            title='Transaction Count',
            overlaying='y',
            side='right'
        )
    )
    
    return fig


def generate_dashboard_charts(user=None):
    """
    Generate all dashboard charts for e-commerce analytics
    
    Args:
        user: Optional user to filter by (for vendor dashboards)
    """
    from .models import Payment
    
    # Base queryset
    qs = Payment.objects.filter(status='Paid')
    
    if user:
        # For vendor dashboards
        qs = qs.filter(
            order__items__product__vendor=user.vendor_profile
        ).distinct()
    
    # Generate all charts
    charts = {
        'revenue_over_time': plot_revenue_over_time(qs, 'day').to_json(),
        'payment_method_distribution': plot_payment_method_distribution(qs).to_json(),
        'category_revenue': plot_category_revenue(qs).to_json(),
        'top_products': plot_top_products(qs, 10).to_json(),
        'daily_transaction_volume': plot_daily_transaction_volume(qs).to_json(),
        'conversion_funnel': plot_conversion_funnel(qs).to_json(),
        'average_order_value': plot_average_order_value_trend(qs).to_json(),
    }
    
    # Calculate summary statistics
    summary = {
        'total_revenue': float(qs.aggregate(total=Sum('amount'))['total'] or 0),
        'total_transactions': qs.count(),
        'average_order_value': float(qs.aggregate(avg=Avg('amount'))['avg'] or 0),
        'success_rate': (qs.count() / Payment.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count() * 100) if Payment.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count() > 0 else 0,
    }
    
    # Get recent transactions
    recent_transactions = list(qs.order_by('-created_at')[:10].values(
        'transaction_reference', 'amount', 'status',
        'created_at', 'payment_method'
    ))
    
    return {
        'charts': charts,
        'summary': summary,
        'recent_transactions': recent_transactions
    }