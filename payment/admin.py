from django.contrib import admin

from .models import Payment, PaystackTransaction
# Register your models here.
admin.site.register(Payment)
admin.site.register(PaystackTransaction)
