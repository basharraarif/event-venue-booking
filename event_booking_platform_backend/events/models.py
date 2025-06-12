from django.db import models
from django.conf import settings
# Assuming venues.models.Venue exists. If not, this will cause an error later.
# It's better to import explicitly if possible to catch issues early.
# from venues.models import Venue
# For now, using a string reference 'venues.Venue' is safer if unsure about import paths during model definition.

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Event(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('past', 'Past'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    # Using string reference for ForeignKey to avoid circular import issues
    # and issues if the app/model isn't loaded yet.
    venue = models.ForeignKey('venues.Venue', related_name='events', on_delete=models.CASCADE)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='organized_events', on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, related_name='events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum capacity for this event. If blank, venue capacity will be used.")

    def __str__(self):
        return self.name

    @property
    def effective_capacity(self):
        if self.max_capacity is not None:
            return self.max_capacity
        return self.venue.capacity if self.venue else 0

    def confirmed_tickets_count(self):
        from django.db.models import Sum
        # Sum of tickets for all CONFIRMED bookings for this event.
        # Assumes Booking model has a status field and 'CONFIRMED' is a valid status.
        # This will require importing Booking model or accessing it carefully to avoid circular imports if called from Booking model context.
        # For now, assuming Booking model and its statuses are defined elsewhere and accessible.
        # A common approach is to use string 'bookings.Booking' if models are in different apps.
        # However, since this method is on Event, and Booking has a ForeignKey to Event,
        # self.bookings should be the related manager.
        # The status 'CONFIRMED' should match the choices in the Booking model.
        # Example: Booking.BookingStatus.CONFIRMED or 'confirmed' if it's a string.
        from bookings.models import Booking # Import here to avoid potential circular import issues at module level
        return self.bookings.filter(status=Booking.BookingStatus.CONFIRMED).aggregate(total_tickets=Sum('number_of_tickets'))['total_tickets'] or 0

    # Example custom validation (optional, but good practice)
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})

    # save method could also be overridden if needed, e.g., to call clean()
    # def save(self, *args, **kwargs):
    #     self.full_clean() # Not always recommended to call full_clean in save
    #     super().save(*args, **kwargs)
