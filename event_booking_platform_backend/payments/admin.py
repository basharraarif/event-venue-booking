from django.contrib import admin
from .models import Payment

# Register your models here.
# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = ('id', 'booking', 'amount', 'currency', 'status', 'payment_gateway_charge_id', 'created_at', 'updated_at')
#     list_filter = ('status', 'currency', 'created_at')
#     search_fields = ('id', 'booking__id', 'payment_gateway_charge_id')
#     readonly_fields = ('id', 'created_at', 'updated_at')
