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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # Example custom validation (optional, but good practice)
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})

    # save method could also be overridden if needed, e.g., to call clean()
    # def save(self, *args, **kwargs):
    #     self.full_clean() # Not always recommended to call full_clean in save
    #     super().save(*args, **kwargs)
