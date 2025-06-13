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
        if self.max_capacity is not None and self.max_capacity > 0: # Consider 0 as explicitly no capacity from event override
            return self.max_capacity
        if self.venue and self.venue.capacity > 0:
            return self.venue.capacity
        # If event.max_capacity is 0, or venue.capacity is 0 or not set,
        # this indicates no defined capacity limit according to Option B (unlimited)
        # or specific handling for 0. For now, let's say 0 from event means 0,
        # but if venue capacity is 0, it might mean "not specified, so unlimited".
        # Task states: "if no capacity is defined at event or venue level, booking proceeds"
        # This means if effective_capacity resolves to 0 or None here, it's "unlimited".
        # The check logic in the view will handle "unlimited" if this returns 0 or None.
        # Let's refine to return None for "unlimited" or a very large number if a number is always needed.
        # For now, returning 0 if not specified, and view logic will treat 0 from here as "no limit".
        # However, if event.max_capacity is explicitly 0, that should mean zero.
        if self.max_capacity == 0: # Explicitly set to zero by admin/organizer
             return 0
        if self.venue and self.venue.capacity is not None: # Venue capacity might be 0
            return self.venue.capacity # Could be 0, meaning venue effectively has no bookable capacity unless event overrides
        return None # Represents "no capacity limit defined"

    def active_tickets_count(self):
        """
        Calculates the current number of active tickets for the event.
        Active tickets are those from bookings in 'confirmed' or 'pending_payment' status.
        """
        from django.db.models import Sum
        from bookings.models import Booking # Import here to avoid potential circular import issues

        active_statuses = [
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.PENDING_PAYMENT
        ]

        query = self.bookings.filter(status__in=active_statuses).aggregate(total_tickets=Sum('number_of_tickets'))
        return query['total_tickets'] or 0

    # Example custom validation (optional, but good practice)
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})

    # save method could also be overridden if needed, e.g., to call clean()
    # def save(self, *args, **kwargs):
    #     self.full_clean() # Not always recommended to call full_clean in save
    #     super().save(*args, **kwargs)
