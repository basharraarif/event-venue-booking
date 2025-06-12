from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'amount', 'currency', 'status', 'transaction_id', 'payment_method', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method', 'currency', 'created_at')
    search_fields = ('id', 'booking__id', 'transaction_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'transaction_id')
