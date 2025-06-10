from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):

    class Roles(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        ORGANIZER = 'organizer', _('Event Organizer')
        VENUE_MANAGER = 'venue_manager', _('Venue Manager')
        # Add more roles as needed, e.g., ADMIN for platform admin distinct from superuser

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    roles = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CUSTOMER,
        verbose_name=_('Role'),
        help_text=_('The primary role of the user on the platform.')
    )

    def __str__(self):
        return self.username

    # Example methods to check roles, can be expanded
    @property
    def is_customer(self):
        return self.roles == self.Roles.CUSTOMER

    @property
    def is_organizer(self):
        return self.roles == self.Roles.ORGANIZER

    @property
    def is_venue_manager(self):
        return self.roles == self.Roles.VENUE_MANAGER

    # If you plan to use Django's built-in permissions system heavily,
    # you might also consider assigning users to Groups that represent these roles,
    # especially if roles come with a predefined set of permissions.
    # For now, this CharField is a simpler approach for role differentiation.
