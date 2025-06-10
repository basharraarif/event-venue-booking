from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
# from events.models import Event # Avoid direct import for model definition if possible

class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    event = models.ForeignKey('events.Event', related_name='bookings', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='bookings', on_delete=models.CASCADE)
    number_of_tickets = models.PositiveIntegerField(default=1)
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False) # editable=False as it's calculated

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

        if self.event and hasattr(self.event, 'ticket_price') and self.event.ticket_price is not None:
            self.total_price = self.event.ticket_price * self.number_of_tickets
        else:
            # This case should ideally not happen if data integrity is maintained (event always has a price).
            # Consider raising an error or logging if event.ticket_price is None.
            self.total_price = 0

        # Calling full_clean() here ensures model validation is run.
        # It's generally good for data integrity but be aware it can raise ValidationError.
        if kwargs.get('force_insert', False) or kwargs.get('force_update', False) or not self.pk:
             # Only call full_clean if it's a new object or forced, to avoid issues with partial updates if fields are missing
             # However, for calculation logic like total_price, better to ensure all required fields (event, number_of_tickets) are present.
             pass # Decided to rely on form/serializer validation primarily for clean() calls.

        super().save(*args, **kwargs)
