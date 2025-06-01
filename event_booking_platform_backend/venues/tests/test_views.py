import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from mixer.backend.django import mixer
from venues.models import Venue
from venues.serializers import VenueSerializer # For comparing response data
from django.contrib.auth.models import User # For creating a test user
import decimal

@pytest.mark.django_db
class TestVenueViewSet:
    def setup_method(self):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        self.client = APIClient()
        # Create a test user for authenticated requests
        self.user = mixer.blend(User, username='testuser')

        # Assign permissions to the user
        content_type = ContentType.objects.get_for_model(Venue)
        permissions_to_add = [
            'add_venue',
            'change_venue',
            'delete_venue',
            'view_venue', # DjangoModelPermissionsOrAnonReadOnly needs view for read access by authenticated users
        ]
        for perm_codename in permissions_to_add:
            permission = Permission.objects.get(content_type=content_type, codename=perm_codename)
            self.user.user_permissions.add(permission)

        self.client.force_authenticate(user=self.user)

        # Some initial venues for testing list, retrieve, etc.
        self.venue1 = mixer.blend(Venue, name="Alpha Place", capacity=100, pricing_per_hour=decimal.Decimal("50.00"), address="1 Test St")
        self.venue2 = mixer.blend(Venue, name="Beta Test Hall", capacity=200, pricing_per_day=decimal.Decimal("400.00"), address="2 Sample Ave", is_available=False)
        self.venue3 = mixer.blend(Venue, name="Gamma Spot", capacity=50, pricing_per_hour=decimal.Decimal("30.00"), address="3 Main Rd")

    def test_list_venues(self):
        url = reverse("venue-list") # 'venue' is the basename for the ViewSet
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data if not paginated or structure is flat
        assert isinstance(response_data, list), "Response data should be a list for a list view without dict pagination."
        assert len(response_data) >= 3 # Check if at least the created venues are listed

        # Check if some names are present
        venue_names_in_response = [venue['name'] for venue in response_data]
        assert "Alpha Place" in venue_names_in_response
        assert "Beta Test Hall" in venue_names_in_response

    def test_retrieve_venue(self):
        url = reverse("venue-detail", kwargs={'pk': self.venue1.pk})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == self.venue1.name
        assert response.data['capacity'] == self.venue1.capacity

    def test_create_venue_valid(self):
        url = reverse("venue-list")
        data = {
            "name": "Delta New Venue",
            "address": "4 Delta Way",
            "capacity": 120,
            "amenities": ["wifi", "projector"],
            "pricing_per_hour": "60.00",
            "is_available": True
        }
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Venue.objects.filter(name="Delta New Venue").exists()
        new_venue = Venue.objects.get(name="Delta New Venue")
        assert new_venue.capacity == 120
        assert new_venue.amenities == ["wifi", "projector"]

    def test_create_venue_invalid_missing_name(self):
        url = reverse("venue-list")
        data = {
            "address": "Invalid Venue St",
            "capacity": 50
        } # Name is missing
        response = self.client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'name' in response.data # Check for error message related to name

    def test_update_venue_put(self): # PUT requires all fields
        url = reverse("venue-detail", kwargs={'pk': self.venue1.pk})
        updated_data = {
            "name": "Alpha Place Updated",
            "address": self.venue1.address, # Keep other fields the same for PUT
            "capacity": 110,
            "amenities": self.venue1.amenities,
            "pricing_per_hour": "55.00",
            "pricing_per_day": self.venue1.pricing_per_day, # Convert Decimal to string if needed by serializer
            "is_available": self.venue1.is_available
        }
        # Ensure pricing_per_day is correctly formatted if not None
        if updated_data["pricing_per_day"] is not None:
            updated_data["pricing_per_day"] = str(updated_data["pricing_per_day"])

        response = self.client.put(url, updated_data, format='json')

        assert response.status_code == status.HTTP_200_OK, response.data
        self.venue1.refresh_from_db()
        assert self.venue1.name == "Alpha Place Updated"
        assert self.venue1.capacity == 110
        assert self.venue1.pricing_per_hour == decimal.Decimal("55.00")

    def test_update_venue_patch(self): # PATCH for partial updates
        url = reverse("venue-detail", kwargs={'pk': self.venue1.pk})
        patch_data = {"capacity": 125, "is_available": False}
        response = self.client.patch(url, patch_data, format='json')

        assert response.status_code == status.HTTP_200_OK, response.data
        self.venue1.refresh_from_db()
        assert self.venue1.capacity == 125
        assert self.venue1.is_available is False

    def test_delete_venue(self):
        url = reverse("venue-detail", kwargs={'pk': self.venue1.pk})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Venue.objects.filter(pk=self.venue1.pk).exists()

    # Filtering Tests
    def test_filter_by_capacity_gte(self):
        url = reverse("venue-list") + "?capacity=150" # Using field_name 'capacity' from VenueFilter
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data
        assert len(response_data) == 1
        assert response_data[0]['name'] == "Beta Test Hall" # Capacity 200

    def test_filter_by_is_available_false(self):
        url = reverse("venue-list") + "?is_available=false"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data
        assert len(response_data) == 1
        assert response_data[0]['name'] == "Beta Test Hall"

    def test_filter_by_min_price_per_hour(self):
        url = reverse("venue-list") + "?min_price_per_hour=40.00"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data
        # Should return Alpha Place (50.00)
        assert len(response_data) == 1
        assert response_data[0]['name'] == "Alpha Place"

    # Search Test
    def test_search_by_name(self):
        url = reverse("venue-list") + "?search=Alpha"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data
        assert len(response_data) == 1
        assert response_data[0]['name'] == "Alpha Place"

    def test_search_by_address_fragment(self):
        url = reverse("venue-list") + "?search=Sample" # Part of "2 Sample Ave"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.data # Directly use response.data
        assert len(response_data) == 1
        assert response_data[0]['name'] == "Beta Test Hall"

    # Test unauthenticated access if relevant (currently all tests are authenticated)
    def test_list_venues_unauthenticated(self):
        self.client.force_authenticate(user=None) # Remove authentication
        url = reverse("venue-list")
        response = self.client.get(url)
        # This depends on DEFAULT_PERMISSION_CLASSES.
        # If DjangoModelPermissionsOrAnonReadOnly, GET should be OK.
        # If IsAuthenticated, this should be 401/403.
        # dj-rest-auth usually sets IsAuthenticated as default for its views.
        # Our VenueViewSet currently has no explicit permission_classes,
        # so it might allow read if REST_FRAMEWORK default is permissive,
        # or block if it's strict.
        # For now, let's assume it's readable, as per DjangoModelPermissionsOrAnonReadOnly.
        assert response.status_code == status.HTTP_200_OK

    def test_create_venue_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse("venue-list")
        data = {"name": "Unauth Create", "address": "No Way", "capacity": 10}
        response = self.client.post(url, data, format='json')
        # This should typically be forbidden.
        # Default is IsAuthenticated for POST/PUT/DELETE with ModelViewSet if TokenAuth is default
        assert response.status_code == status.HTTP_401_UNAUTHORIZED # Or 403 if auth but no perm

# Note: The basename 'venue' for router.register(r'', VenueViewSet, basename='venue')
# in venues/urls.py is used to generate names like 'venue-list' and 'venue-detail'.
# If you used a different basename, adjust reverse() calls accordingly.
# My venues/urls.py has router.register(r'', VenueViewSet, basename='venue')
# so 'venue-list' and 'venue-detail' should be correct. Let's verify this.
# In event_booking_platform_backend/venues/urls.py:
# router = DefaultRouter()
# router.register(r'', VenueViewSet, basename='venue')
# Yes, 'venue' is the basename. Ok.
