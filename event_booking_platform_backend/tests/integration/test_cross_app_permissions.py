import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from core.models import Role
from events.models import Event, Venue, Category
from bookings.models import Booking # For testing booking access

User = get_user_model()

@pytest.mark.django_db
class TestCrossAppPermissions:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def common_roles(self):
        # Ensure roles are created once
        customer, _ = Role.objects.get_or_create(name=Role.CUSTOMER)
        organizer, _ = Role.objects.get_or_create(name=Role.EVENT_ORGANIZER)
        manager, _ = Role.objects.get_or_create(name=Role.VENUE_MANAGER)
        admin, _ = Role.objects.get_or_create(name=Role.ADMIN)
        return {'customer': customer, 'organizer': organizer, 'manager': manager, 'admin': admin}

    @pytest.fixture
    def customer_user(self, common_roles):
        user = User.objects.create_user(username='customer_only', email='customer@perm.test', password='password')
        user.roles.add(common_roles['customer'])
        return user

    @pytest.fixture
    def event_organizer_user(self, common_roles):
        user = User.objects.create_user(username='organizer_only', email='organizer@perm.test', password='password')
        user.roles.add(common_roles['organizer'])
        return user

    @pytest.fixture
    def venue_manager_user(self, common_roles):
        user = User.objects.create_user(username='manager_only', email='manager@perm.test', password='password')
        user.roles.add(common_roles['manager'])
        return user

    @pytest.fixture
    def admin_user(self, common_roles):
        user = User.objects.create_user(username='admin_perm', email='admin@perm.test', password='password', is_staff=True) # Admins are staff
        user.roles.add(common_roles['admin'])
        return user

    @pytest.fixture
    def sample_venue(self, admin_user): # Admin user creates a venue for general use in tests
        return Venue.objects.create(name="Test Venue Global", address="123 Global St", capacity=100, owner=admin_user)

    @pytest.fixture
    def sample_category(self):
        return Category.objects.create(name="Test Category Global")

    @pytest.fixture
    def sample_event(self, sample_venue, admin_user, sample_category): # Admin user creates an event
        event = Event.objects.create(
            name="Test Event Global",
            venue=sample_venue,
            organizer=admin_user,
            ticket_price=20.00,
            start_time="2029-01-01T10:00:00Z",
            end_time="2029-01-01T12:00:00Z",
            status=Event.EventStatus.UPCOMING
        )
        event.categories.add(sample_category)
        return event

    # --- Venue Access Tests ---
    def test_event_organizer_cannot_manage_venues(self, api_client, event_organizer_user, sample_venue):
        api_client.force_authenticate(user=event_organizer_user)

        # Create venue
        venue_create_url = reverse('venue-list')
        venue_data = {'name': 'New Venue by Org', 'address': 'Org Address', 'capacity': 50, 'owner': event_organizer_user.pk} # owner might be ignored or auto-set
        response = api_client.post(venue_create_url, venue_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Update venue
        venue_detail_url = reverse('venue-detail', kwargs={'pk': sample_venue.pk})
        response = api_client.patch(venue_detail_url, {'name': 'Updated by Org'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Delete venue
        response = api_client.delete(venue_detail_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # List venues (should be allowed by IsAuthenticatedOrReadOnly)
        response = api_client.get(venue_create_url)
        assert response.status_code == status.HTTP_200_OK

        # Retrieve venue (should be allowed by IsAuthenticatedOrReadOnly)
        response = api_client.get(venue_detail_url)
        assert response.status_code == status.HTTP_200_OK


    # --- Event Access Tests ---
    def test_venue_manager_cannot_manage_events(self, api_client, venue_manager_user, sample_event, sample_venue):
        api_client.force_authenticate(user=venue_manager_user)

        # Create event
        event_create_url = reverse('event-list')
        event_data = {
            'name': 'New Event by VM', 'venue': sample_venue.pk, 'ticket_price': 10,
            'start_time': "2029-02-01T10:00:00Z", 'end_time': "2029-02-01T12:00:00Z",
            'organizer': venue_manager_user.pk # organizer might be auto-set or ignored
        }
        response = api_client.post(event_create_url, event_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Update event
        event_detail_url = reverse('event-detail', kwargs={'pk': sample_event.pk})
        response = api_client.patch(event_detail_url, {'name': 'Updated by VM'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Delete event
        response = api_client.delete(event_detail_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # List events (should be allowed by IsAuthenticatedOrReadOnly)
        response = api_client.get(event_create_url)
        assert response.status_code == status.HTTP_200_OK

        # Retrieve event (should be allowed by IsAuthenticatedOrReadOnly)
        response = api_client.get(event_detail_url)
        assert response.status_code == status.HTTP_200_OK

    # --- Customer Access Tests ---
    def test_customer_cannot_access_management_endpoints(self, api_client, customer_user, sample_venue, sample_event):
        api_client.force_authenticate(user=customer_user)

        # Venue management attempts
        venue_list_url = reverse('venue-list')
        venue_detail_url = reverse('venue-detail', kwargs={'pk': sample_venue.pk})
        venue_data = {'name': 'New Venue by Cust', 'address': 'Cust Address', 'capacity': 30}

        response = api_client.post(venue_list_url, venue_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response = api_client.patch(venue_detail_url, {'name': 'Updated by Cust'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response = api_client.delete(venue_detail_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Event management attempts
        event_list_url = reverse('event-list')
        event_detail_url = reverse('event-detail', kwargs={'pk': sample_event.pk})
        event_data = {'name': 'New Event by Cust', 'venue': sample_venue.pk, 'ticket_price': 5}

        response = api_client.post(event_list_url, event_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response = api_client.patch(event_detail_url, {'name': 'Updated by Cust'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response = api_client.delete(event_detail_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Listing and Retrieving Venues/Events should be allowed for customers
        response = api_client.get(venue_list_url)
        assert response.status_code == status.HTTP_200_OK
        response = api_client.get(venue_detail_url)
        assert response.status_code == status.HTTP_200_OK
        response = api_client.get(event_list_url)
        assert response.status_code == status.HTTP_200_OK
        response = api_client.get(event_detail_url)
        assert response.status_code == status.HTTP_200_OK

    def test_customer_booking_access(self, api_client, customer_user, admin_user, sample_event):
        api_client.force_authenticate(user=customer_user)

        # Customer creates their own booking
        booking_list_url = reverse('booking-list')
        booking_data = {'event': sample_event.pk, 'number_of_tickets': 1}
        response = api_client.post(booking_list_url, booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        own_booking_id = response.data['id']
        own_booking_url = reverse('booking-detail', kwargs={'pk': own_booking_id})

        # Customer can list their own bookings (queryset filtering will apply)
        response = api_client.get(booking_list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == own_booking_id

        # Customer can retrieve their own booking
        response = api_client.get(own_booking_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == own_booking_id

        # Create another booking by a different user (admin for simplicity)
        api_client.force_authenticate(user=admin_user)
        other_booking_data = {'event': sample_event.pk, 'number_of_tickets': 1, 'user': admin_user.pk}
        # Admin might need to specify user if serializer allows, or it defaults to request.user.
        # The BookingViewSet perform_create sets user=request.user.
        # So, admin books for themselves here.
        response_admin_booking = api_client.post(booking_list_url, other_booking_data, format='json')
        assert response_admin_booking.status_code == status.HTTP_201_CREATED
        other_users_booking_id = response_admin_booking.data['id']
        other_users_booking_url = reverse('booking-detail', kwargs={'pk': other_users_booking_id})

        # Customer attempts to access the other user's booking
        api_client.force_authenticate(user=customer_user)
        response = api_client.get(other_users_booking_url)
        # IsOwnerOrAdmin permission should deny access (403) or if filtered out by queryset, it would be 404.
        # Given IsOwnerOrAdmin is explicitly checked for retrieve, 403 is more likely for direct access attempt.
        # BookingViewSet.get_queryset() filters, so if the ID is not in the filtered list, DRF might return 404 first.
        # Let's check for either. IsOwnerOrAdmin.has_object_permission returning False leads to 403.
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

        # Customer tries to list all bookings - should only see their own
        response = api_client.get(booking_list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1 # Should still be 1 (only their own)
        booking_ids_in_list = [b['id'] for b in response.data['results']]
        assert own_booking_id in booking_ids_in_list
        assert other_users_booking_id not in booking_ids_in_list

    # Add more tests for event organizer managing their own events vs others,
    # and venue manager managing their own venues vs others.
    def test_event_organizer_manages_own_vs_others_events(self, api_client, event_organizer_user, admin_user, sample_venue, sample_category):
        # Event Organizer creates their own event
        api_client.force_authenticate(user=event_organizer_user)
        event_create_url = reverse('event-list')
        own_event_data = {
            'name': 'EO Own Event', 'venue': sample_venue.pk, 'ticket_price': 15,
            'start_time': "2029-03-01T10:00:00Z", 'end_time': "2029-03-01T12:00:00Z",
            'status': Event.EventStatus.UPCOMING
            # Organizer is set by perform_create
        }
        response = api_client.post(event_create_url, own_event_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        own_event_id = response.data['id']
        own_event_url = reverse('event-detail', kwargs={'pk': own_event_id})

        # EO can update their own event
        response = api_client.patch(own_event_url, {'name': 'EO Own Event Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin creates another event
        api_client.force_authenticate(user=admin_user)
        other_event_data = {
            'name': 'Admin Event', 'venue': sample_venue.pk, 'ticket_price': 25,
            'organizer': admin_user.pk, # Admin sets self as organizer
            'start_time': "2029-04-01T10:00:00Z", 'end_time': "2029-04-01T12:00:00Z",
            'status': Event.EventStatus.UPCOMING
        }
        response_admin_event = api_client.post(event_create_url, other_event_data, format='json')
        assert response_admin_event.status_code == status.HTTP_201_CREATED
        other_event_id = response_admin_event.data['id']
        other_event_url = reverse('event-detail', kwargs={'pk': other_event_id})

        # EO tries to update Admin's event
        api_client.force_authenticate(user=event_organizer_user)
        response = api_client.patch(other_event_url, {'name': 'EO Tries Update Other Event'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN # IsEventOrganizer checks obj.organizer

        # EO can delete their own event
        response = api_client.delete(own_event_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # EO cannot delete Admin's event
        response = api_client.delete(other_event_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_venue_manager_manages_own_vs_others_venues(self, api_client, venue_manager_user, admin_user):
        # Venue Manager creates their own venue
        api_client.force_authenticate(user=venue_manager_user)
        venue_create_url = reverse('venue-list')
        own_venue_data = {'name': 'VM Own Venue', 'address': 'VM Address', 'capacity': 70}
        response = api_client.post(venue_create_url, own_venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        own_venue_id = response.data['id']
        own_venue_url = reverse('venue-detail', kwargs={'pk': own_venue_id})

        # VM can update their own venue
        response = api_client.patch(own_venue_url, {'name': 'VM Own Venue Updated'}, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Admin creates another venue
        api_client.force_authenticate(user=admin_user)
        other_venue_data = {'name': 'Admin Venue', 'address': 'Admin Address', 'capacity': 120, 'owner': admin_user.pk}
        response_admin_venue = api_client.post(venue_create_url, other_venue_data, format='json')
        assert response_admin_venue.status_code == status.HTTP_201_CREATED
        other_venue_id = response_admin_venue.data['id']
        other_venue_url = reverse('venue-detail', kwargs={'pk': other_venue_id})

        # VM tries to update Admin's venue
        api_client.force_authenticate(user=venue_manager_user)
        response = api_client.patch(other_venue_url, {'name': 'VM Tries Update Other Venue'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN # IsVenueManager checks obj.owner

        # VM can delete their own venue
        response = api_client.delete(own_venue_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # VM cannot delete Admin's venue
        response = api_client.delete(other_venue_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_event_organizer_can_list_bookings_for_own_events(self, api_client, event_organizer_user, customer_user, sample_venue, sample_category):
        # Organizer creates an event
        api_client.force_authenticate(user=event_organizer_user)
        event_data = {'name': 'Org Event Bookings', 'venue': sample_venue.pk, 'ticket_price': 10, 'start_time': "2029-05-01T10:00:00Z", 'end_time': "2029-05-01T12:00:00Z"}
        response = api_client.post(reverse('event-list'), event_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        org_event_id = response.data['id']

        # Customer books this event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': org_event_id, 'number_of_tickets': 1}
        response = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking_id = response.data['id']

        # Organizer lists bookings - should see the booking for their event
        api_client.force_authenticate(user=event_organizer_user)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0 # Check if list is not empty
        assert any(b['id'] == booking_id for b in response.data['results']), "Booking for organizer's event not found in list"

        # Organizer retrieves that specific booking
        response = api_client.get(reverse('booking-detail', kwargs={'pk': booking_id}))
        assert response.status_code == status.HTTP_200_OK # Or 403 if only admin/owner can retrieve directly
                                                        # Current BookingViewSet.get_queryset allows this if event organizer matches
                                                        # And IsOwnerOrAdmin for retrieve might need adjustment or specific check.
                                                        # For now, assume get_queryset allows retrieve.

    def test_venue_manager_can_list_bookings_for_own_venues(self, api_client, venue_manager_user, event_organizer_user, customer_user, sample_category):
        # Venue Manager creates a venue
        api_client.force_authenticate(user=venue_manager_user)
        venue_data = {'name': 'VM Venue Bookings', 'address': 'VM Venue St', 'capacity': 50}
        response = api_client.post(reverse('venue-list'), venue_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        vm_venue_id = response.data['id']

        # Event organizer creates an event at VM's venue
        api_client.force_authenticate(user=event_organizer_user)
        event_data = {'name': 'Event at VM Venue', 'venue': vm_venue_id, 'ticket_price': 10, 'start_time': "2029-06-01T10:00:00Z", 'end_time': "2029-06-01T12:00:00Z"}
        response = api_client.post(reverse('event-list'), event_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_id_at_vm_venue = response.data['id']

        # Customer books this event
        api_client.force_authenticate(user=customer_user)
        booking_data = {'event': event_id_at_vm_venue, 'number_of_tickets': 1}
        response = api_client.post(reverse('booking-list'), booking_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        booking_id = response.data['id']

        # Venue Manager lists bookings - should see the booking for event at their venue
        api_client.force_authenticate(user=venue_manager_user)
        response = api_client.get(reverse('booking-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
        assert any(b['id'] == booking_id for b in response.data['results']), "Booking for event at manager's venue not found"
