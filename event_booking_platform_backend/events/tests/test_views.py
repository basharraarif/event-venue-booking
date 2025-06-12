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

        # Create Roles
        self.event_organizer_role, _ = Role.objects.get_or_create(name='EVENT_ORGANIZER')
        self.venue_manager_role, _ = Role.objects.get_or_create(name='VENUE_MANAGER')
        self.regular_user_role, _ = Role.objects.get_or_create(name='REGULAR_USER')

        # Create Users
        self.admin_user = User.objects.create_superuser('admin_event', 'admin_event@example.com', 'adminpass')

        self.event_organizer_user = User.objects.create_user('eventorg1', 'eo1@example.com', 'eopass')
        self.event_organizer_user.roles.add(self.event_organizer_role)

        self.another_event_organizer = User.objects.create_user('eventorg2', 'eo2@example.com', 'eopass2')
        self.another_event_organizer.roles.add(self.event_organizer_role)

        self.venue_manager_user = User.objects.create_user('vm_event', 'vm_event@example.com', 'vmpass')
        self.venue_manager_user.roles.add(self.venue_manager_role)

        self.regular_user = User.objects.create_user('reg_event', 'reg_event@example.com', 'regpass')
        self.regular_user.roles.add(self.regular_user_role)

        # Common Venue (owned by admin or a generic user for simplicity)
        self.venue_owner = User.objects.create_user('venueown_event', 'voe@example.com', 'vopass')
        self.venue = mixer.blend(Venue, name="Test Venue for Events", owner=self.venue_owner)
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

    def test_list_events_authenticated_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.event_list_create_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3

    def test_retrieve_event_authenticated_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == self.event_by_eo1.name

    def test_create_event_as_event_organizer(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        data = {
            "name": "New Event by EO1", "venue": self.venue.pk, "categories": [self.category.pk],
            "start_time": timezone.now() + timezone.timedelta(days=5),
            "end_time": timezone.now() + timezone.timedelta(days=5, hours=2),
            "ticket_price": "50.00", "description": "A new event.",
            "organizer": self.event_organizer_user.id # EO should set themselves as organizer
        }
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Event.objects.filter(name="New Event by EO1", organizer=self.event_organizer_user).exists()

    def test_create_event_as_regular_user_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {"name": "Regular User Event Fail", "venue": self.venue.pk, "ticket_price": "10.00", "organizer": self.regular_user.id}
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_event_as_venue_manager_forbidden(self):
        self.client.force_authenticate(user=self.venue_manager_user)
        data = {"name": "VM Event Fail", "venue": self.venue.pk, "ticket_price": "10.00", "organizer": self.venue_manager_user.id}
        response = self.client.post(self.event_list_create_url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_own_event_as_event_organizer(self):
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        data = {"ticket_price": "25.50"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.event_by_eo1.refresh_from_db()
        assert self.event_by_eo1.ticket_price == decimal.Decimal("25.50")

    def test_update_event_as_event_organizer_role_not_owner_allowed(self):
        # Scenario: EO1 has EVENT_ORGANIZER role, tries to update event organized by EO2.
        # IsEventModificationAllowed should permit this if user has EVENT_ORGANIZER role, even if not the direct organizer field owner.
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_other_eo.pk})
        data = {"description": "Updated by another EO with role"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        self.event_by_other_eo.refresh_from_db()
        assert self.event_by_other_eo.description == "Updated by another EO with role"

    def test_update_event_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk}) # Admin updates EO1's event
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

    def test_delete_event_as_event_organizer_role_not_owner_allowed(self):
        # EO1 (with role) deletes event organized by EO2
        self.client.force_authenticate(user=self.event_organizer_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_other_eo.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Event.objects.filter(pk=self.event_by_other_eo.pk).exists()

    def test_delete_event_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Event.objects.filter(pk=self.event_by_eo1.pk).exists()

    def test_regular_user_cannot_update_event(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        data = {"name": "Attempted Update by Regular User"}
        response = self.client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_cannot_delete_event(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("event-detail", kwargs={'pk': self.event_by_eo1.pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
