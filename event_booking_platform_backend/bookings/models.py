from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal # Import Decimal for default values
# from events.models import Event # Avoid direct import for model definition if possible

class Booking(models.Model):
    class BookingStatus(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        PENDING = 'pending', 'Pending'
        PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
        # Add other statuses as needed, e.g. PAYMENT_FAILED

    event = models.ForeignKey('events.Event', related_name='bookings', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='bookings', on_delete=models.CASCADE)
    number_of_tickets = models.PositiveIntegerField(default=1)
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING
    )
    price_per_ticket_at_booking = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, # Will be set on first save
        blank=True # Should not be user-editable directly in forms if logic handles it
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    payment_intent_id = models.CharField(max_length=255, null=True, blank=True, help_text="Stripe PaymentIntent ID, if applicable.")

    def __str__(self):
        return f"Booking for {self.event.name} by {self.user.username} ({self.number_of_tickets} tickets)"

    def clean(self):
        super().clean()
        if self.number_of_tickets <= 0:
            raise ValidationError({'number_of_tickets': 'Number of tickets must be greater than zero.'})
        # Potentially add checks related to event capacity if that logic is added to Event model
        # For example:
        # if self.event.bookings.aggregate(sum('number_of_tickets'))['number_of_tickets__sum'] + self.number_of_tickets > self.event.venue.capacity:
        #     raise ValidationError('Not enough tickets available for this event.')
        # This kind of check is complex for clean() and better handled in form/serializer or view if it involves existing bookings.

    def save(self, *args, **kwargs):
        # Calculate total_price before saving
        # self.event should be a model instance here if the Booking instance is properly constructed.
        # If self.event is just an ID (e.g. during some forms of object creation not via ORM),
        # you'd need to fetch the event object first.
        # However, when a Booking instance is saved, self.event is already the related Event instance.

        # Set price_per_ticket_at_booking only on first save (when pk is None or price_per_ticket_at_booking is not set)
        if not self.pk or self.price_per_ticket_at_booking is None:
            if self.event and hasattr(self.event, 'ticket_price') and self.event.ticket_price is not None:
                self.price_per_ticket_at_booking = self.event.ticket_price
            else:
                # Handle case where event price might be missing (e.g. if event is deleted or misconfigured)
                # This should ideally be prevented by data integrity at event level.
                # For now, setting to 0 or raising an error are options. Let's default to 0 if not found.
                self.price_per_ticket_at_booking = self.price_per_ticket_at_booking or Decimal('0.00')

        # Calculate total_price based on the stored price_per_ticket_at_booking
        if self.price_per_ticket_at_booking is not None and self.number_of_tickets is not None:
            self.total_price = self.price_per_ticket_at_booking * self.number_of_tickets
        else:
            self.total_price = Decimal('0.00') # Default if something is missing

        # Calling full_clean() here ensures model validation is run.
        # It's generally good for data integrity but be aware it can raise ValidationError.
        if kwargs.get('force_insert', False) or kwargs.get('force_update', False) or not self.pk:
             # Only call full_clean if it's a new object or forced, to avoid issues with partial updates if fields are missing
             # However, for calculation logic like total_price, better to ensure all required fields (event, number_of_tickets) are present.
             pass # Decided to rely on form/serializer validation primarily for clean() calls.

        super().save(*args, **kwargs)

    def is_payment_required(self):
        """
        Checks if payment is required for this booking based on its total price.
        """
        return self.total_price is not None and self.total_price > Decimal('0.00')