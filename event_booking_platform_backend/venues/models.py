from django.db import models

class Venue(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    capacity = models.IntegerField()
    amenities = models.JSONField(default=list) # Using JSONField, default to empty list
    pricing_per_hour = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pricing_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Venue'
        verbose_name_plural = 'Venues'
