from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class Role(models.Model):
    # Define role names as constants for easier reference elsewhere
    ADMIN = 'ADMIN'
    EVENT_ORGANIZER = 'EVENT_ORGANIZER'
    VENUE_MANAGER = 'VENUE_MANAGER'
    CUSTOMER = 'CUSTOMER'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (EVENT_ORGANIZER, 'Event Organizer'),
        (VENUE_MANAGER, 'Venue Manager'),
        (CUSTOMER, 'Customer'),
    ]
    name = models.CharField(max_length=50, unique=True, choices=ROLE_CHOICES)

    def __str__(self):
        return self.get_name_display()

class User(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")

    def __str__(self):
        return self.username
