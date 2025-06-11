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
        choices=[
            ('pending', 'Pending'),
            ('requires_action', 'Requires Action'), # For 3D Secure
            ('succeeded', 'Succeeded'), # Changed from 'successful' to align with Stripe
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
            ('cancelled', 'Cancelled'), # Added for PaymentIntents that are cancelled
        ],
        default='pending'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe PaymentIntent ID (pi_...)" )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} for Booking {self.booking.id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
