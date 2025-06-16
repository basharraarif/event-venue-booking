import uuid
from django.db import models
from django.conf import settings
from bookings.models import Booking

class Payment(models.Model):
    """
    Represents a payment for a booking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in major currency units (e.g., USD, EUR)")
    currency = models.CharField(max_length=3, default='USD') # ISO 4217 currency code
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('succeeded', 'Succeeded'), ('failed', 'Failed')],
        default='pending'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, unique=True, help_text="Stripe PaymentIntent ID")
    payment_method = models.CharField(max_length=50, default='simulated_card') # This might be removed or changed depending on how Stripe Elements is implemented
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} for Booking {self.booking.id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=['status']),
            # booking is OneToOneField, implicitly indexed.
            # stripe_payment_intent_id is unique=True, so already indexed.
        ]
