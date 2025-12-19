from django.urls import path
from .views import (
    InitializePaymentView,
    PaystackWebhookView,
    PaymentViewSet,
    PaystackCallbackView,
)

app_name = 'payments'

urlpatterns = [
    # Analytics URLs
    path('history/', PaymentViewSet.as_view(), name='payments'),
    #  Callback URL - where Paystack redirects after payment
    path('callback/', PaystackCallbackView.as_view(), name='paystack_callback'),
    
    # Payment endpoints
    path('initialize/', InitializePaymentView.as_view(), name='initialize-payment'),
   
    # Webhook
    path('webhook/paystack/', PaystackWebhookView.as_view(), name='paystack-webhook'),
]