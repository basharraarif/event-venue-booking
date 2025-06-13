import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from mixer.backend.django import mixer
from django.contrib.auth import get_user_model
from events.models import Event, Category
from venues.models import Venue
from core.models import Role # Import Role
import decimal

User = get_user_model()

@pytest.mark.django_db
class TestEventViewSetPermissions:
    def setup_method(self):
        self.client = APIClient()

        # Create Roles based on new model definitions
        self.event_organizer_role, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        self.venue_manager_role, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)
        self.customer_role, _ = Role.objects.get_or_create(name=Role.CUSTOMER) # Changed from REGULAR_USER
        self.admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)

        # Create Users
        self.admin_user = User.objects.create_superuser('admin_event', 'admin_event@example.com', 'adminpass')
        self.admin_user.roles.add(self.admin_role) # Assign ADMIN role

        self.event_organizer_user = User.objects.create_user('eventorg1', 'eo1@example.com', 'eopass')
        self.event_organizer_user.roles.add(self.event_organizer_role)

        self.another_event_organizer = User.objects.create_user('eventorg2', 'eo2@example.com', 'eopass2')
        self.another_event_organizer.roles.add(self.event_organizer_role)

        self.venue_manager_user = User.objects.create_user('vm_event', 'vm_event@example.com', 'vmpass')
        self.venue_manager_user.roles.add(self.venue_manager_role)

        self.customer_user = User.objects.create_user('customer_event', 'cust_event@example.com', 'custpass') # Changed from regular_user
        self.customer_user.roles.add(self.customer_role)

        # Common Venue (owned by admin or a generic user for simplicity)
        self.venue_owner = User.objects.create_user('venueown_event', 'voe@example.com', 'vopass') # Can be any user
        self.venue = mixer.blend(Venue, name="Test Venue for Events", owner=self.venue_owner) # Venue owner can be different from event players
        self.category = mixer.blend(Category, name="Test Category")

        # Events
        self.event_by_eo1 = mixer.blend(
            Event, name="EO1's Event", venue=self.venue, organizer=self.event_organizer_user,
            start_time=timezone.now() + timezone.timedelta(days=1), ticket_price=20.00
        )
        self.event_by_other_eo = mixer.blend(
            Event, name="Other EO's Event", venue=self.venue, organizer=self.another_event_organizer,
            start_time=timezone.now() + timezone.timedelta(days=2), ticket_price=30.00
        )
        self.event_for_listing = mixer.blend(
            Event, name="General Listing Event", venue=self.venue, organizer=self.admin_user, # Admin organized
            start_time=timezone.now() + timezone.timedelta(days=3), ticket_price=25.00
        )

        self.event_list_create_url = reverse("event-list")

    def test_list_events_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.event_list_create_url)
        assert response.status_code == status.HTTP_200_OK # AllowAny for list/retrieve

    def test_list_events_authenticated_customer_user(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get(self.event_list_create_url)
        assert response.status_code == status.HTTP_200_OK
        # Ensure all public events are listed. Exact count depends on what's created.
        # For this test, we have event_by_eo1, event_by_other_eo, event_for_listing
        assert len(response.data.get('results', response.data)) >= 3


    def test_retrieve_event_authenticated_customer_user(self):
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == self.event_by_eo1.name

    def test_create_event_as_event_organizer(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        data = {
            "name": "New Event by EO1", "venue": self.venue.pk, "categories": [self.category.pk],
            "start_time": (timezone.now() + timezone.timedelta(days=5)).isoformat(),
            "end_time": (timezone.now() + timezone.timedelta(days=5, hours=2)).isoformat(),
            "ticket_price": "50.00", "description": "A new event."
            # Organizer is set by perform_create in the view
        }
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        # Verify that the event was created with the authenticated user as the organizer
        assert Event.objects.filter(name="New Event by EO1", organizer=self.event_organizer_user).exists()

    def test_create_event_as_customer_user_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        data = {"name": "Customer Event Fail", "venue": self.venue.pk, "ticket_price": "10.00"}
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_event_as_venue_manager_forbidden(self): # Assuming VM is not also EO
        self.client.force_authenticate(user=self.venue_manager_user)
        data = {"name": "VM Event Fail", "venue": self.venue.pk, "ticket_price": "10.00"}
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_own_event_as_event_organizer(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        data = {"ticket_price": "25.50"} # Using string for decimal
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.event_by_eo1.refresh_from_db()
        assert self.event_by_eo1.ticket_price == decimal.Decimal("25.50")

    def test_update_others_event_as_event_organizer_forbidden(self):
        # EO1 tries to update event organized by another_event_organizer (EO2)
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_other_eo.pk})
        data = {"description": "Attempted Update by EO1 on EO2's event"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN # New stricter permission

    def test_update_event_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk}) # Admin updates EO1's event (who is not admin)
        data = {"name": "Admin Updated EO1 Event"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.event_by_eo1.refresh_from_db()
        assert self.event_by_eo1.name == "Admin Updated EO1 Event"

    def test_delete_own_event_as_event_organizer(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Event.objects.filter(pk=self.event_by_eo1.pk).exists()

    def test_delete_others_event_as_event_organizer_forbidden(self):
        # EO1 tries to delete event organized by another_event_organizer (EO2)
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_other_eo.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN # New stricter permission

    def test_delete_event_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        # Admin deletes event organized by EO1
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Event.objects.filter(pk=self.event_by_eo1.pk).exists()

    def test_customer_user_cannot_update_event(self):
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        data = {"name": "Attempted Update by Customer User"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_customer_user_cannot_delete_event(self):
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
